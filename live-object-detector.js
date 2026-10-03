/* COCO-SSD browser detector. Boxes are generated locally on the device. */
(function (root) {
  const TFJS_URL = 'https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@4.22.0/dist/tf.min.js';
  const COCO_SSD_URL = 'https://cdn.jsdelivr.net/npm/@tensorflow-models/coco-ssd@2.2.3/dist/coco-ssd.min.js';
  const TARGET_CLASSES = new Set([
    'cell phone', 'laptop', 'keyboard', 'mouse', 'tv', 'remote', 'microwave',
    'refrigerator', 'toaster', 'hair drier', 'oven'
  ]);
  const V1_CLASSES = new Set(['cell phone', 'keyboard', 'mouse']);
  let modelPromise;

  function loadScript(src, globalName) {
    if (root[globalName]) return Promise.resolve();
    const existing = document.querySelector(`script[data-live-model="${globalName}"]`);
    if (existing) return new Promise((resolve, reject) => {
      existing.addEventListener('load', resolve, {once:true});
      existing.addEventListener('error', () => reject(new Error('The live object detector could not be downloaded.')), {once:true});
    });
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = src;
      script.async = true;
      script.crossOrigin = 'anonymous';
      script.dataset.liveModel = globalName;
      script.onload = resolve;
      script.onerror = () => {
        script.remove();
        reject(new Error('The live object detector could not be downloaded. Check your connection and try again.'));
      };
      document.head.appendChild(script);
    });
  }

  class LiveObjectDetector {
    async load() {
      if (!modelPromise) modelPromise = (async () => {
        await loadScript(TFJS_URL, 'tf');
        await root.tf.ready();
        await loadScript(COCO_SSD_URL, 'cocoSsd');
        return root.cocoSsd.load({base:'lite_mobilenet_v2'});
      })().catch(error => { modelPromise = null; throw error; });
      this.model = await modelPromise;
      return this;
    }

    async detect(video) {
      if (!this.model) await this.load();
      const objects = await this.model.detect(video, 10, 0.4);
      return objects.filter(item => TARGET_CLASSES.has(item.class) && item.score >= 0.4);
    }
  }

  if (typeof module !== 'undefined' && module.exports) module.exports = {LiveObjectDetector, TARGET_CLASSES, V1_CLASSES};
  root.LiveObjectDetector = LiveObjectDetector;
})(typeof globalThis !== 'undefined' ? globalThis : window);
