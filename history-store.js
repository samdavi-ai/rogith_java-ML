(function (root, factory) {
  const store = factory();
  if (typeof module === 'object' && module.exports) module.exports = store;
  if (root) root.RecoLensHistory = store;
})(typeof window !== 'undefined' ? window : globalThis, function () {
  const KEY = 'sc-history';
  const LIMIT = 20;

  function read(storage) {
    try {
      const entries = JSON.parse(storage.getItem(KEY) || '[]');
      return Array.isArray(entries) ? entries.filter(entry => entry && typeof entry === 'object') : [];
    } catch (_) {
      return [];
    }
  }

  function save(storage, item) {
    const entries = read(storage);
    entries.unshift(item);
    try {
      storage.setItem(KEY, JSON.stringify(entries.slice(0, LIMIT)));
      return true;
    } catch (_) {
      return false;
    }
  }

  return {read, save};
});
