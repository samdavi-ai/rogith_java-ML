/* Browser camera lifecycle, on-device object boxes, and live V1 classification. */
(function (root) {
  const FRAME_MAX_EDGE = 640;
  const FRAME_QUALITY = 0.78;

  class CameraController {
    constructor({ video, mediaDevices, fetchImpl, formDataFactory, canvasFactory, isMobile, apiBase, detectorFactory, onState, onPrediction, onUnavailable, onNetworkError, onCameraCount, onTorchAvailability, onDetections, onLiveStatus }) {
      this.video = video;
      this.mediaDevices = mediaDevices || root.navigator?.mediaDevices;
      this.fetchImpl = fetchImpl || root.fetch.bind(root);
      this.apiBase = String(apiBase || '').replace(/\/$/, '');
      this.formDataFactory = formDataFactory || (() => new root.FormData());
      this.canvasFactory = canvasFactory || (() => root.document.createElement('canvas'));
      this.detectorFactory = detectorFactory || (async () => new root.LiveObjectDetector().load());
      this.isMobile = isMobile;
      this.onState = onState || (() => {});
      this.onPrediction = onPrediction || (() => {});
      this.onUnavailable = onUnavailable || (() => {});
      this.onNetworkError = onNetworkError || (() => {});
      this.onCameraCount = onCameraCount || (() => {});
      this.onTorchAvailability = onTorchAvailability || (() => {});
      this.onDetections = onDetections || (() => {});
      this.onLiveStatus = onLiveStatus || (() => {});
      this.torchSupported = false;
      this.torchOn = false;
      this.stream = null;
      this.devices = [];
      this.currentDeviceId = null;
      this.abortController = null;
      this.requestInProgress = false;
      this.detector = null;
      this.liveTimer = null;
      this.nextLiveClassificationAt = 0;
      this.liveRetryDelayMs = 2500;
      this.loopGeneration = 0;
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
        if (this.detector) this.startLiveIdentification();
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
      this.cancelPendingClassification();
      this.onState('switching', 'Switching camera…');
      try {
        const nextStream = await this.mediaDevices.getUserMedia({ video: { deviceId: { exact: next.deviceId } }, audio: false });
        await this.attachStream(nextStream);
        this.updateTorchSupport();
        this.stopTracks(oldStream);
        this.currentDeviceId = next.deviceId;
        this.onState('active', 'Camera active.');
        if (this.detector) this.startLiveIdentification();
        return true;
      } catch (error) {
        if (this.stream !== oldStream) this.stopTracks(this.stream);
        this.stream = oldStream;
        this.video.srcObject = oldStream;
        this.onState('active', `Couldn't switch cameras. ${error.message || 'Keep using the current camera.'}`);
        return false;
      }
    }

    async captureAndClassify() {
      if (!this.stream || this.requestInProgress) return false;
      const generation = this.loopGeneration;
      try {
        const frame = await this.captureFrame();
        if (generation !== this.loopGeneration || !this.stream) return false;
        return await this.classifyFrame(frame, generation, false);
      } catch (error) {
        this.onNetworkError(error.message || 'The classification service is unavailable.');
        return false;
      }
    }

    async startLiveIdentification() {
      if (!this.stream) return false;
      this.clearLiveTimer();
      const generation = this.loopGeneration;
      try {
        this.onLiveStatus('Loading live object detection on this device…');
        if (!this.detector) this.detector = await this.detectorFactory();
        if (generation !== this.loopGeneration || !this.stream) return false;
        this.onLiveStatus('Point at an electronic item. Live boxes and identification are starting…');
        this.runLiveDetection(generation);
        return true;
      } catch (error) {
        if (generation === this.loopGeneration) this.onLiveStatus(`Live object detection could not start. ${error.message || ''} You can still capture a photo.`);
        return false;
      }
    }

    async runLiveDetection(generation) {
      if (generation !== this.loopGeneration || !this.stream || !this.detector) return;
      try {
        const detections = await this.detector.detect(this.video);
        if (generation !== this.loopGeneration || !this.stream) return;
        this.onDetections(detections);
        const ordered = detections.slice().sort((a,b) => b.score - a.score);
        const target = ordered.find(item => ['cell phone','keyboard','mouse'].includes(item.class));
        if (!target && !ordered.length) {
          this.onLiveStatus('Looking for a phone, keyboard, mouse, or other visible electronic item…');
        } else if (!target) {
          this.onLiveStatus(`Detected ${ordered[0].class}. Live V1 identification currently supports phones, keyboards, and mice.`);
        } else {
          this.onLiveStatus(`Detected ${target.class} · checking with RecoLens V1…`);
          if (!this.requestInProgress && Date.now() >= this.nextLiveClassificationAt) {
            this.nextLiveClassificationAt = Date.now() + 1800;
            const frame = await this.captureFrame(target.bbox);
            if (generation === this.loopGeneration && this.stream) this.classifyFrame(frame, generation, true, target);
          }
        }
      } catch (error) {
        if (generation === this.loopGeneration) this.onLiveStatus(error.message || 'Live detection paused. You can still capture a photo.');
      } finally {
        if (generation === this.loopGeneration && this.stream) this.liveTimer = setTimeout(() => this.runLiveDetection(generation), 350);
      }
    }

    async classifyFrame(frame, generation, live, detection = null) {
      if (this.requestInProgress || generation !== this.loopGeneration || !this.stream) return false;
      this.requestInProgress = true;
      const controller = new AbortController();
      this.abortController = controller;
      const timeout = setTimeout(() => controller.abort('timeout'), 15000);
      try {
        const body = this.formDataFactory();
        body.append('image', frame, live ? 'live-detected-item.jpg' : 'camera-capture.jpg');
        const response = await this.fetchImpl(`${this.apiBase}/api/classifications`, { method: 'POST', body, signal: controller.signal });
        let result;
        try { result = await response.json(); }
        catch { throw Object.assign(new Error('The classification service returned an unreadable response.'), { code: 'INVALID_RESPONSE' }); }
        if (generation !== this.loopGeneration) return false;
        if (!response.ok) {
          const error = new Error(result?.error?.message || 'The classification service could not analyze this photo.');
          error.code = result?.error?.code;
          error.status = response.status;
          if (error.code === 'MODEL_UNAVAILABLE' || error.code === 'MODEL_LOAD_ERROR') {
            if (live) this.liveRetryDelayMs = 12000;
            this.onUnavailable(error.code === 'MODEL_LOAD_ERROR'
              ? 'Identification is unavailable because the model could not be loaded.'
              : 'Identification is currently unavailable. Please try again later.');
            return false;
          }
          throw error;
        }
        const prediction = result?.data?.classification || result?.data || result?.prediction;
        const isUnsure = prediction?.status === 'UNSURE' || prediction?.confidenceLevel === 'UNSURE';
        const category = isUnsure ? 'UNSURE' : prediction?.categoryName || prediction?.category;
        const confidence = Number(prediction?.confidence);
        if (!category || !Number.isFinite(confidence)) throw Object.assign(new Error('The service response did not contain a valid classification.'), { code: 'INVALID_RESPONSE' });
        if (live) this.liveRetryDelayMs = 2500;
        this.onPrediction({ category, confidence, isUnsure, confidenceLevel: prediction.confidenceLevel, alternatives: prediction.alternatives || [], frame, stable: true, live, detection });
        return true;
      } catch (error) {
        if (generation === this.loopGeneration && !(controller.signal.aborted && controller.signal.reason !== 'timeout')) {
          if (live) this.liveRetryDelayMs = 8000;
          this.onNetworkError(controller.signal.aborted ? 'Classification is taking longer than expected.' : error.message || 'The classification service is unavailable.');
        }
        return false;
      } finally {
        clearTimeout(timeout);
        this.requestInProgress = false;
        if (live) this.nextLiveClassificationAt = Date.now() + this.liveRetryDelayMs;
        if (this.abortController === controller) this.abortController = null;
      }
    }

    async captureFrame(bbox = null) {
      if (!this.video?.videoWidth || !this.video?.videoHeight) throw new Error('The camera is still starting. Wait a moment and try again.');
      let sx = 0, sy = 0, sw = this.video.videoWidth, sh = this.video.videoHeight;
      if (bbox?.length === 4) {
        const padding = 0.14;
        const [x,y,w,h] = bbox;
        sx = Math.max(0, x - w * padding);
        sy = Math.max(0, y - h * padding);
        sw = Math.min(this.video.videoWidth - sx, w * (1 + padding * 2));
        sh = Math.min(this.video.videoHeight - sy, h * (1 + padding * 2));
      }
      const scale = Math.min(1, FRAME_MAX_EDGE / Math.max(sw, sh));
      const canvas = this.canvasFactory();
      canvas.width = Math.max(1, Math.round(sw * scale));
      canvas.height = Math.max(1, Math.round(sh * scale));
      const context = canvas.getContext('2d', { alpha: false });
      context.drawImage(this.video, sx, sy, sw, sh, 0, 0, canvas.width, canvas.height);
      const blob = await new Promise((resolve, reject) => canvas.toBlob(value => value ? resolve(value) : reject(new Error('Could not capture a camera frame.')), 'image/jpeg', FRAME_QUALITY));
      if (blob.size > 10 * 1024 * 1024) throw new Error('Captured frame is too large. Try a lower-resolution camera.');
      return blob;
    }

    cancelPendingClassification() {
      this.loopGeneration++;
      this.abortController?.abort('camera stopped');
      this.clearLiveTimer();
      this.onDetections([]);
    }

    clearLiveTimer() { if (this.liveTimer) clearTimeout(this.liveTimer); this.liveTimer = null; }

    stop(state = 'stopped', message = 'Camera stopped.') {
      this.cancelPendingClassification();
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

  if (typeof module !== 'undefined' && module.exports) module.exports = { CameraController };
  root.CameraController = CameraController;
})(typeof globalThis !== 'undefined' ? globalThis : window);
