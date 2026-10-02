const test = require('node:test');
const assert = require('node:assert/strict');
const { CameraController } = require('../camera-controller.js');

function makeStream(id = 'camera-a') {
  const track = { stopped: false, stop() { this.stopped = true; }, getSettings() { return { deviceId: id }; } };
  return { track, getTracks() { return [track]; }, getVideoTracks() { return [track]; } };
}
function makeController(overrides = {}) {
  const states = [], fetchCalls = [], cameraCounts = [], predictions = [], unavailable = [], networkErrors = [];
  const video = { videoWidth: 1280, videoHeight: 720, srcObject: null, play: async () => {} };
  const streams = [makeStream('camera-a'), makeStream('camera-b')];
  const deviceRequests = [];
  const mediaDevices = {
    async getUserMedia(constraints) { deviceRequests.push(constraints); return streams.shift() || makeStream('camera-extra'); },
    async enumerateDevices() { return [{kind:'videoinput',deviceId:'camera-a'}, {kind:'videoinput',deviceId:'camera-b'}]; }
  };
  const options = {
    video, mediaDevices,
    canvasFactory: () => ({
      width: 0, height: 0,
      getContext: () => ({drawImage() {}}),
      toBlob(callback, type, quality) { this.encoded = {type,quality,width:this.width,height:this.height}; callback(new Blob(['frame'], {type})); }
    }),
    formDataFactory: () => ({append(name, blob, filename) { this.entry = {name,blob,filename}; }}),
    fetchImpl: async (url, init) => { fetchCalls.push({url,init}); return {ok:false,status:503,json:async()=>({error:{code:'MODEL_UNAVAILABLE',message:'No model'}})}; },
    onState: (state,message) => states.push({state,message}),
    onPrediction: prediction => predictions.push(prediction),
    onUnavailable: message => unavailable.push(message),
    onNetworkError: message => networkErrors.push(message),
    onCameraCount: count => cameraCounts.push(count),
    ...overrides
  };
  return {controller:new CameraController(options),video,streams,deviceRequests,fetchCalls,states,cameraCounts,predictions,unavailable,networkErrors};
}
async function flush() { await new Promise(resolve => setTimeout(resolve, 5)); }

test('uses a real video-only desktop stream and exposes camera switching only when multiple inputs exist', async () => {
  const fixture = makeController();
  assert.equal(await fixture.controller.start(), true);
  assert.deepEqual(fixture.deviceRequests[0], {video:true,audio:false});
  assert.ok(fixture.video.srcObject);
  assert.equal(fixture.cameraCounts.at(-1), 2);
  fixture.controller.stop();
  assert.equal(fixture.video.srcObject, null);
});

test('prefers the mobile rear camera and never asks for microphone access', () => {
  const fixture = makeController({isMobile:true});
  assert.deepEqual(fixture.controller.initialConstraints(), {video:{facingMode:{ideal:'environment'}},audio:false});
});

test('maps denied and missing-camera permissions to actionable states', async t => {
  await t.test('permission denied', async () => {
    const fixture = makeController({mediaDevices:{getUserMedia:async()=>{throw Object.assign(new Error(),{name:'NotAllowedError'});}}});
    assert.equal(await fixture.controller.start(), false);
    assert.equal(fixture.states.at(-1).state, 'permission-denied');
  });
  await t.test('no camera', async () => {
    const fixture = makeController({mediaDevices:{getUserMedia:async()=>{throw Object.assign(new Error(),{name:'NotFoundError'});}}});
    assert.equal(await fixture.controller.start(), false);
    assert.equal(fixture.states.at(-1).state, 'no-camera');
  });
});

test('reports unsupported camera APIs without requesting a stream', async () => {
  const fixture = makeController({mediaDevices:null});
  assert.equal(await fixture.controller.start(),false);
  assert.equal(fixture.states.at(-1).state,'unsupported');
});

test('switches camera only after the replacement stream is ready, then stops the old track', async () => {
  const fixture = makeController();
  await fixture.controller.start();
  const oldStream = fixture.video.srcObject;
  assert.equal(await fixture.controller.switchCamera(), true);
  assert.equal(fixture.deviceRequests.at(-1).video.deviceId.exact, 'camera-b');
  assert.equal(oldStream.track.stopped, true);
  assert.notEqual(fixture.video.srcObject, oldStream);
  fixture.controller.stop();
});

test('captures a downscaled JPEG frame without sending the video stream', async () => {
  let canvas;
  const fixture = makeController({canvasFactory:() => (canvas = {
    width:0,height:0,getContext:()=>({drawImage(){}}),toBlob(callback,type,quality){this.encoded={type,quality};callback(new Blob(['frame'],{type}));}
  })});
  const frame = await fixture.controller.captureFrame();
  assert.equal(canvas.width,640);
  assert.equal(canvas.height,360);
  assert.equal(canvas.encoded.type,'image/jpeg');
  assert.ok(canvas.encoded.quality < 1);
  assert.equal(frame.type,'image/jpeg');
  assert.equal(fixture.fetchCalls.length,0);
});

test('keeps a real camera preview idle until a user capture, then reports model unavailability', async () => {
  const fixture = makeController();
  await fixture.controller.start();
  assert.equal(fixture.fetchCalls.length,0);
  assert.equal(await fixture.controller.captureAndClassify(),false);
  await flush();
  assert.equal(fixture.fetchCalls.length,1);
  assert.equal(fixture.fetchCalls[0].url,'/api/classifications');
  assert.equal(fixture.fetchCalls[0].init.method,'POST');
  assert.ok(fixture.fetchCalls[0].init.body.entry.blob instanceof Blob);
  assert.match(fixture.fetchCalls[0].init.body.entry.filename,/camera-capture\.jpg/);
  assert.equal(fixture.unavailable.length,1);
  assert.ok(fixture.video.srcObject);
  assert.equal(fixture.video.srcObject.track.stopped,false);
  fixture.controller.stop();
});

test('reports a non-sensitive message on MODEL_LOAD_ERROR after an explicit capture', async () => {
  const fixture = makeController({fetchImpl:async()=>({ok:false,status:503,json:async()=>({error:{code:'MODEL_LOAD_ERROR',message:'load failed'}})})});
  await fixture.controller.start();
  await fixture.controller.captureAndClassify();
  await flush();
  assert.match(fixture.unavailable[0],/model could not be loaded/i);
  fixture.controller.stop();
});

test('uses the configured HTTPS API origin for a separately hosted production frontend', async () => {
  const fixture = makeController({apiBase:'https://ewaste-api.onrender.com/'});
  await fixture.controller.start();
  await fixture.controller.captureAndClassify();
  assert.equal(fixture.fetchCalls[0].url,'https://ewaste-api.onrender.com/api/classifications');
  fixture.controller.stop();
});

test('does not run two capture requests at once and aborts a pending request when stopped', async () => {
  let calls = 0, aborted = false;
  const fixture = makeController({fetchImpl:(_url,init) => {
    calls++;
    return new Promise((resolve,reject) => init.signal.addEventListener('abort',() => {aborted=true;reject(new DOMException('Aborted','AbortError'));},{once:true}));
  }});
  await fixture.controller.start();
  const pending = fixture.controller.captureAndClassify();
  await flush();
  assert.equal(calls,1);
  assert.equal(await fixture.controller.captureAndClassify(),false);
  fixture.controller.stop();
  await pending;
  await flush();
  assert.equal(aborted,true);
  assert.equal(fixture.video.srcObject,null);
});

test('returns one explicit capture classification without inventing a category for UNSURE', async () => {
  const fixture = makeController({fetchImpl:async()=>({ok:true,status:200,json:async()=>({data:{classification:{status:'UNSURE',categoryName:null,confidence:.56,confidenceLevel:'UNSURE'}}})})});
  await fixture.controller.start();
  assert.equal(await fixture.controller.captureAndClassify(),true);
  assert.equal(fixture.predictions.length,1);
  assert.equal(fixture.predictions[0].category,'UNSURE');
  assert.equal(fixture.predictions[0].isUnsure,true);
  assert.equal(fixture.predictions[0].stable,true);
  fixture.controller.stop();
});

test('renders the category and confidence from a successful explicit capture response', async () => {
  const fixture = makeController({fetchImpl:async()=>({ok:true,status:200,json:async()=>({data:{classification:{status:'CLASSIFIED',categoryName:'Mobile phone',confidence:.9913,confidenceLevel:'HIGH'}}})})});
  await fixture.controller.start();
  assert.equal(await fixture.controller.captureAndClassify(),true);
  assert.equal(fixture.predictions[0].category,'Mobile phone');
  assert.equal(fixture.predictions[0].confidence,.9913);
  fixture.controller.stop();
});
