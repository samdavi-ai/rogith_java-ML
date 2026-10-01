/* Browser camera lifecycle and sampled classification requests. No frame is retained here. */
(function (root) {
  const DEFAULT_INTERVAL_MS = 1000;
  const FRAME_MAX_EDGE = 640;
  const FRAME_QUALITY = 0.78;
  const HISTORY_SIZE = 5;
  const MIN_STABLE_VOTES = 3;

  class CameraController {
    constructor({ video, mediaDevices, intervalMs, fetchImpl, formDataFactory, canvasFactory, visibilityState, isMobile, apiBase, onState, onPrediction, onUnavailable, onNetworkError, onCameraCount, onTorchAvailability }) {
      this.video = video;
      this.mediaDevices = mediaDevices || root.navigator?.mediaDevices;
      this.intervalMs = Math.max(250, Number(intervalMs) || DEFAULT_INTERVAL_MS);
      this.fetchImpl = fetchImpl || root.fetch.bind(root);
      this.apiBase = String(apiBase || '').replace(/\/$/, '');
      this.formDataFactory = formDataFactory || (() => new root.FormData());
      this.canvasFactory = canvasFactory || (() => root.document.createElement('canvas'));
      this.visibilityState = visibilityState || (() => root.document?.visibilityState);
      this.isMobile = isMobile;
      this.onState = onState || (() => {});
      this.onPrediction = onPrediction || (() => {});
      this.onUnavailable = onUnavailable || (() => {});
      this.onNetworkError = onNetworkError || (() => {});
      this.onCameraCount = onCameraCount || (() => {});
      this.onTorchAvailability = onTorchAvailability || (() => {});
      this.torchSupported = false;
      this.torchOn = false;
      this.stream = null;
      this.devices = [];
      this.currentDeviceId = null;
      this.timer = null;
      this.abortController = null;
      this.requestInProgress = false;
      this.loopGeneration = 0;
      this.inferenceEnabled = false;
      this.failedRequests = 0;
      this.recentPredictions = [];
      this.deviceChangeAttached = false;
      this.handleDeviceChange = async () => {
        if (!this.stream) return;
        this.devices = await this.enumerateCameras();
        this.onCameraCount(this.devices.length);
      };
    }

    async start() {
      if (!this.mediaDevices?.getUserMedia) {
        this.onState('unsupported', 'Live camera detection is not supported by this browser.');
        return false;
      }
      if (this.stream) return true;
      this.onState('requesting', 'Requesting camera access…');
      const constraints = this.initialConstraints();
      try {
        let stream;
        try {
          stream = await this.mediaDevices.getUserMedia(constraints);
        } catch (error) {
          if (constraints.video !== true && error.name === 'OverconstrainedError') {
            stream = await this.mediaDevices.getUserMedia({ video: true, audio: false });
          } else throw error;
        }
        await this.attachStream(stream);
        this.updateTorchSupport();
        this.devices = await this.enumerateCameras();
        this.mediaDevices.addEventListener?.('devicechange', this.handleDeviceChange);
        this.deviceChangeAttached = true;
        this.currentDeviceId = stream.getVideoTracks()[0]?.getSettings?.().deviceId || null;
        this.onCameraCount(this.devices.length);
        this.onState('active', 'Camera active.');
        this.beginInference();
        return true;
      } catch (error) {
        this.stopTracks(this.stream);
        this.stream = null;
        if (this.video) this.video.srcObject = null;
        const [state, message] = this.cameraError(error);
        this.onState(state, message);
        return false;
      }
    }

    initialConstraints() {
      const isMobile = this.isMobile === undefined
        ? Boolean(root.matchMedia?.('(max-width: 700px)').matches || /Android|iPhone|iPad|iPod/i.test(root.navigator?.userAgent || ''))
        : Boolean(typeof this.isMobile === 'function' ? this.isMobile() : this.isMobile);
      return isMobile
        ? { video: { facingMode: { ideal: 'environment' } }, audio: false }
        : { video: true, audio: false };
    }

    async attachStream(stream) {
      this.video.srcObject = stream;
      this.stream = stream;
      try {
        await this.video.play();
      } catch (error) {
        this.stopTracks(stream);
        this.video.srcObject = null;
        this.stream = null;
        throw Object.assign(new Error('Camera preview could not start. Check browser playback settings and try again.'), { name: 'PlaybackError', cause: error });
      }
    }

    async enumerateCameras() {
      if (!this.mediaDevices?.enumerateDevices) return [];
      try {
        return (await this.mediaDevices.enumerateDevices()).filter(device => device.kind === 'videoinput');
      } catch { return []; }
    }

    updateTorchSupport() {
      const track = this.stream?.getVideoTracks?.()[0];
      this.torchSupported = Boolean(track?.getCapabilities?.().torch);
      this.torchOn = false;
      this.onTorchAvailability(this.torchSupported, this.torchOn);
    }

    async toggleTorch() {
      const track = this.stream?.getVideoTracks?.()[0];
      if (!this.torchSupported || !track?.applyConstraints) return false;
      const nextState = !this.torchOn;
      try {
        await track.applyConstraints({ advanced: [{ torch: nextState }] });
        this.torchOn = nextState;
        this.onTorchAvailability(true, this.torchOn);
        return true;
      } catch {
        this.torchSupported = false;
        this.torchOn = false;
        this.onTorchAvailability(false, false);
        return false;
      }
    }

    async switchCamera() {
      if (!this.stream) return false;
      this.devices = await this.enumerateCameras();
      this.onCameraCount(this.devices.length);
      if (this.devices.length < 2) return false;
      const current = this.devices.findIndex(device => device.deviceId === this.currentDeviceId);
      const next = this.devices[(current + 1 + this.devices.length) % this.devices.length];
      const oldStream = this.stream;
      this.pauseInference();
      this.onState('switching', 'Switching camera…');
      try {
        const nextStream = await this.mediaDevices.getUserMedia({ video: { deviceId: { exact: next.deviceId } }, audio: false });
        await this.attachStream(nextStream);
        this.updateTorchSupport();
        this.stopTracks(oldStream);
        this.currentDeviceId = next.deviceId;
        this.onState('active', 'Camera active.');
        this.beginInference();
        return true;
      } catch (error) {
        if (this.stream !== oldStream) this.stopTracks(this.stream);
        this.stream = oldStream;
        this.video.srcObject = oldStream;
        this.onState('active', `Couldn't switch cameras. ${error.message || 'Keep using the current camera.'}`);
        this.beginInference();
        return false;
      }
    }

    async captureFrame() {
      if (!this.video?.videoWidth || !this.video?.videoHeight) throw new Error('The camera is still starting. Wait a moment and try again.');
      const scale = Math.min(1, FRAME_MAX_EDGE / Math.max(this.video.videoWidth, this.video.videoHeight));
      const canvas = this.canvasFactory();
      canvas.width = Math.max(1, Math.round(this.video.videoWidth * scale));
      canvas.height = Math.max(1, Math.round(this.video.videoHeight * scale));
      const context = canvas.getContext('2d', { alpha: false });
      context.drawImage(this.video, 0, 0, canvas.width, canvas.height);
      const blob = await new Promise((resolve, reject) => canvas.toBlob(value => value ? resolve(value) : reject(new Error('Could not capture a camera frame.')), 'image/jpeg', FRAME_QUALITY));
      if (blob.size > 10 * 1024 * 1024) throw new Error('Captured frame is too large. Try a lower-resolution camera.');
      return blob;
    }

    beginInference() {
      if (!this.stream) return;
      this.inferenceEnabled = true;
      this.recentPredictions = [];
      this.failedRequests = 0;
      const generation = ++this.loopGeneration;
      this.schedule(generation, 0);
    }

    schedule(generation, delay = this.intervalMs) {
      clearTimeout(this.timer);
      if (!this.stream || !this.inferenceEnabled || generation !== this.loopGeneration) return;
      this.timer = setTimeout(() => this.runInference(generation), delay);
    }

    async runInference(generation) {
      if (!this.stream || !this.inferenceEnabled || generation !== this.loopGeneration || this.visibilityState() === 'hidden') return;
      if (this.requestInProgress) { this.schedule(generation); return; }
      this.requestInProgress = true;
      const controller = new AbortController();
      this.abortController = controller;
      const timeout = setTimeout(() => controller.abort('timeout'), 8000);
      try {
        const frame = await this.captureFrame();
        if (generation !== this.loopGeneration || controller.signal.aborted) return;
        const body = this.formDataFactory();
        body.append('image', frame, 'camera-frame.jpg');
        const response = await this.fetchImpl(`${this.apiBase}/api/classifications`, { method: 'POST', body, signal: controller.signal });
        let result;
        try { result = await response.json(); }
        catch { throw Object.assign(new Error('The classification service returned an unreadable response.'), { code: 'INVALID_RESPONSE' }); }
        if (generation !== this.loopGeneration) return;
        if (!response.ok) {
          const error = new Error(result?.error?.message || 'The classification service could not analyze this frame.');
          error.code = result?.error?.code;
          error.status = response.status;
          if (error.code === 'MODEL_UNAVAILABLE' || error.code === 'MODEL_LOAD_ERROR') {
            this.inferenceEnabled = false;
            clearTimeout(this.timer);
            this.onUnavailable(error.code === 'MODEL_LOAD_ERROR'
              ? 'Live identification is currently unavailable because the model could not be loaded.'
              : 'Live identification is currently unavailable. A trained classification model has not been configured yet.');
            return;
          }
          throw error;
        }
        this.failedRequests = 0;
        const prediction = result?.data?.classification || result?.data || result?.prediction;
        const isUnsure = prediction?.status === 'UNSURE' || prediction?.confidenceLevel === 'UNSURE';
        const category = isUnsure ? 'UNSURE' : prediction?.categoryName || prediction?.category;
        const confidence = Number(prediction?.confidence);
        if (!category || !Number.isFinite(confidence)) throw Object.assign(new Error('The service response did not contain a valid classification.'), { code: 'INVALID_RESPONSE' });
        this.acceptPrediction({ category, confidence, isUnsure, confidenceLevel: prediction.confidenceLevel, alternatives: prediction.alternatives || [], frame });
      } catch (error) {
        if (generation !== this.loopGeneration || controller.signal.aborted && controller.signal.reason !== 'timeout') return;
        this.failedRequests++;
        if (controller.signal.aborted && controller.signal.reason === 'timeout') this.onNetworkError('Classification is taking longer than expected.');
        else this.onNetworkError(error.status === 0 ? 'No connection to the classification service.' : error.message || 'Camera is working, but the classification service is unavailable.');
        if (this.failedRequests >= 3) {
          this.inferenceEnabled = false;
          this.onNetworkError('Live requests are paused after repeated service errors. Retry classification when the service is available.');
        }
      } finally {
        clearTimeout(timeout);
        this.requestInProgress = false;
        if (this.abortController === controller) this.abortController = null;
        if (generation === this.loopGeneration) this.schedule(generation);
      }
    }

    acceptPrediction(prediction) {
      this.recentPredictions.push(prediction);
      if (this.recentPredictions.length > HISTORY_SIZE) this.recentPredictions.shift();
      const counts = new Map();
      for (const entry of this.recentPredictions) counts.set(entry.category, (counts.get(entry.category) || 0) + 1);
      const [category, votes] = [...counts.entries()].sort((a, b) => b[1] - a[1])[0];
      if (votes < MIN_STABLE_VOTES) {
        this.onPrediction({ ...prediction, stable: false });
        return;
      }
      const matching = this.recentPredictions.filter(entry => entry.category === category);
      const average = matching.reduce((sum, entry) => sum + entry.confidence, 0) / matching.length;
      this.onPrediction({ ...matching[matching.length - 1], category, confidence: average, stable: true });
    }

    retryInference() {
      if (!this.stream) return;
      this.failedRequests = 0;
      this.recentPredictions = [];
      this.inferenceEnabled = true;
      const generation = ++this.loopGeneration;
      this.schedule(generation, 0);
    }

    pauseInference() {
      this.inferenceEnabled = false;
      this.loopGeneration++;
      clearTimeout(this.timer);
      this.timer = null;
      this.abortController?.abort('camera stopped');
    }

    stop(state = 'stopped', message = 'Camera stopped.') {
      this.pauseInference();
      const stream = this.stream;
      this.stream = null;
      if (this.deviceChangeAttached) this.mediaDevices?.removeEventListener?.('devicechange', this.handleDeviceChange);
      this.deviceChangeAttached = false;
      this.stopTracks(stream);
      if (this.video) this.video.srcObject = null;
      this.currentDeviceId = null;
      this.torchSupported = false;
      this.torchOn = false;
      this.onTorchAvailability(false, false);
      this.devices = [];
      this.onCameraCount(0);
      this.onState(state, message);
    }

    stopTracks(stream) {
      stream?.getTracks?.().forEach(track => track.stop());
    }

    cameraError(error) {
      if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError' || error.name === 'SecurityError')
        return ['permission-denied', 'Camera access was denied. Allow camera access in your browser settings and try again.'];
      if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError')
        return ['no-camera', 'No camera was detected.'];
      if (error.name === 'NotReadableError' || error.name === 'TrackStartError')
        return ['in-use', 'The camera is currently being used by another application.'];
      if (error.name === 'PlaybackError') return ['error', error.message];
      return ['error', 'We couldn’t start the camera. Check your browser settings and try again.'];
    }
  }

  if (typeof module !== 'undefined' && module.exports) module.exports = { CameraController, DEFAULT_INTERVAL_MS };
  root.CameraController = CameraController;
})(typeof globalThis !== 'undefined' ? globalThis : window);
