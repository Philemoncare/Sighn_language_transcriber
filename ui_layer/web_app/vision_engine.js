/**
 * Signly Vision Engine (Universal Communication Hub v11)
 * Optimized for real-time sign language translation and multi-user video meetings.
 */

class VisionEngine {
    constructor(videoElement, canvasElement, options = {}) {
        this.video = videoElement;
        this.canvas = canvasElement;
        this.ctx = this.canvas.getContext('2d');

        // Configuration
        this.options = {
            mirrorPreview: options.mirrorPreview ?? true,
            showLandmarks: options.showLandmarks ?? true,
            fpsTarget: options.fpsTarget ?? 60,
            aiEnabled: options.aiEnabled ?? true,
            modelComplexity: options.modelComplexity ?? 0,
            ...options
        };

        // State
        this.isActive = false;
        this.isProcessing = false;
        this.holistic = null;
        this.socket = null;
        this.stream = null;
        this.currentFacingMode = 'user';
        navigator.mediaDevices.addEventListener('devicechange', () => this._enumerateDevices());

        // Meeting & WebRTC State
        this.currentRoomId = null;
        this.peerConnections = {}; // userId -> RTCPeerConnection
        this.remoteStreams = {}; // userId -> MediaStream
        this.iceServers = { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }, { urls: 'stun:stun1.l.google.com:19302' }] };
        this.micEnabled = true;
        this.cameraEnabled = true;
        this.isHandRaised = false;
        this.isScreenSharing = false;
        this.screenStream = null;

        // Device Management
        this.videoDevices = [];
        this.currentDeviceIndex = 0;

        // Metrics
        this.metrics = {
            fps: 0,
            inferenceTime: 0,
            handDetected: false,
            trackingQuality: 0,
            status: 'IDLE'
        };

        this._frameCount = 0;
        this._lastTime = performance.now();
        this._renderLoopId = null;
    }

    async initialize() {
        this.metrics.status = 'INITIALIZING';
        try {
            await this._enumerateDevices();
            this.holistic = new Holistic({
                locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/holistic/${file}`
            });
            this._applyModelSettings();
            this.holistic.onResults((results) => this._onResults(results));
            this._connectSocket();
            this.metrics.status = 'READY';
        } catch (e) {
            console.error('Vision Engine: Init error', e);
            this.metrics.status = 'ERROR_INIT';
        }
    }

    async _enumerateDevices() {
        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            this.videoDevices = devices.filter(d => d.kind === 'videoinput');
        } catch (e) { console.error('Device enumeration failed', e); }
    }

    _applyModelSettings() {
        if (!this.holistic) return;
        this.holistic.setOptions({
            modelComplexity: this.options.modelComplexity,
            smoothLandmarks: true,
            minDetectionConfidence: 0.5,
            minTrackingConfidence: 0.5,
            refineFaceLandmarks: false
        });
    }

    _connectSocket() {
        if (this.socket) this.socket.close();
        const token = localStorage.getItem('snlag_token');
        const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const host = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
            ? 'localhost:8000' : window.location.host;

        this.socket = new WebSocket(`${proto}://${host}/ws/translate?token=${token}`);
        this.socket.onopen = () => console.log('Vision Engine: Connected to core.');

        this.socket.onmessage = (event) => {
            if (typeof event.data === 'string') {
                try {
                    const data = JSON.parse(event.data);
                    this._handleSocketMessage(data);
                } catch(e) { console.error('WS Data Error', e); }
            }
        };

        this.socket.onclose = () => {
            if (this.isActive) setTimeout(() => this._connectSocket(), 3000);
        };
    }

    _handleSocketMessage(data) {
        const userId = data.sender_id;
        switch (data.type) {
            case 'prediction':
                this._emit('signly-prediction', data);
                break;
            case 'remote_translation':
                this._emit('meeting-remote-translation', data);
                break;
            case 'participant_joined':
                this._initiatePeerConnection(data.user_id, true);
                break;
            case 'participant_left':
                this._removePeerConnection(data.user_id);
                break;
            case 'room_state':
                data.participants.forEach(p => this._initiatePeerConnection(p.user_id, true));
                break;
            case 'webrtc_offer':
                this._handleOffer(userId, data.offer);
                break;
            case 'webrtc_answer':
                this._handleAnswer(userId, data.answer);
                break;
            case 'webrtc_ice_candidate':
                this._handleIceCandidate(userId, data.candidate);
                break;
            case 'meeting_action':
                this._emit('meeting-remote-action', data);
                break;
        }
    }

    /**
     * WEBRTC SIGNALING
     */
    async joinRoom(roomId) {
        this.currentRoomId = roomId;
        this._send({ type: 'join_room', room_id: roomId });
    }

    async _initiatePeerConnection(userId, isOffer) {
        if (this.peerConnections[userId]) return;
        const pc = new RTCPeerConnection(this.iceServers);
        this.peerConnections[userId] = pc;

        pc.onicecandidate = (e) => {
            if (e.candidate) this._send({ type: 'webrtc_ice_candidate', target_id: userId, candidate: e.candidate });
        };

        pc.ontrack = (e) => {
            this.remoteStreams[userId] = e.streams[0];
            this._emit('meeting-remote-stream', { userId, stream: e.streams[0] });
        };

        const currentStream = this.isScreenSharing ? this.screenStream : this.stream;
        if (currentStream) {
            currentStream.getTracks().forEach(track => pc.addTrack(track, currentStream));
        }

        if (isOffer) {
            const offer = await pc.createOffer();
            await pc.setLocalDescription(offer);
            this._send({ type: 'webrtc_offer', target_id: userId, offer });
        }
        return pc;
    }

    async _handleOffer(userId, offer) {
        const pc = await this._initiatePeerConnection(userId, false);
        await pc.setRemoteDescription(new RTCSessionDescription(offer));
        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);
        this._send({ type: 'webrtc_answer', target_id: userId, answer });
    }

    async _handleAnswer(userId, answer) {
        const pc = this.peerConnections[userId];
        if (pc) await pc.setRemoteDescription(new RTCSessionDescription(answer));
    }

    async _handleIceCandidate(userId, candidate) {
        const pc = this.peerConnections[userId];
        if (pc) await pc.addIceCandidate(new RTCIceCandidate(candidate));
    }

    _removePeerConnection(userId) {
        if (this.peerConnections[userId]) {
            this.peerConnections[userId].close();
            delete this.peerConnections[userId];
            delete this.remoteStreams[userId];
            this._emit('meeting-remote-left', { userId });
        }
    }

    /**
     * CAMERA & MEDIA
     */
    async start() {
        if (this.isActive) return;
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: this.currentFacingMode, width: 1280, height: 720 },
                audio: true
            });
            this.video.srcObject = this.stream;
            await new Promise(r => this.video.onloadedmetadata = r);
            this.isActive = true;
            this._renderLoop();
        } catch (e) {
            console.error('Camera access denied', e);
            throw e;
        }
    }

    stop() {
        this.isActive = false;
        if (this.stream) this.stream.getTracks().forEach(t => t.stop());
        cancelAnimationFrame(this._renderLoopId);
        Object.values(this.peerConnections).forEach(pc => pc.close());
        this.peerConnections = {};
    }

    toggleMic() {
        this.micEnabled = !this.micEnabled;
        if (this.stream) this.stream.getAudioTracks().forEach(t => t.enabled = this.micEnabled);
        this._broadcastAction({ action: 'mic', state: this.micEnabled });
        return this.micEnabled;
    }

    toggleCamera() {
        this.cameraEnabled = !this.cameraEnabled;
        if (this.stream) this.stream.getVideoTracks().forEach(t => t.enabled = this.cameraEnabled);
        this._broadcastAction({ action: 'camera', value: this.cameraEnabled });
        return this.cameraEnabled;
    }

    toggleHandRaise() {
        this.isHandRaised = !this.isHandRaised;
        this._broadcastAction({ action: 'hand_raise', value: this.isHandRaised });
        return this.isHandRaised;
    }

    async toggleScreenShare() {
        if (this.isScreenSharing) {
            this.isScreenSharing = false;
            if (this.screenStream) {
                this.screenStream.getTracks().forEach(t => t.stop());
                this.screenStream = null;
            }
            this._replaceVideoTrack(this.stream.getVideoTracks()[0]);
        } else {
            try {
                this.screenStream = await navigator.mediaDevices.getDisplayMedia({ video: true });
                this.isScreenSharing = true;
                const screenTrack = this.screenStream.getVideoTracks()[0];
                screenTrack.onended = () => this.toggleScreenShare();
                this._replaceVideoTrack(screenTrack);
            } catch (e) {
                console.error('Screen share denied', e);
                return false;
            }
        }
        return this.isScreenSharing;
    }

    async cycleCamera() {
        if (this.videoDevices.length < 2) return;
        this.currentDeviceIndex = (this.currentDeviceIndex + 1) % this.videoDevices.length;
        const deviceId = this.videoDevices[this.currentDeviceIndex].deviceId;

        const newStream = await navigator.mediaDevices.getUserMedia({
            video: { deviceId: { exact: deviceId }, width: 1280, height: 720 },
            audio: true
        });

        const newVideoTrack = newStream.getVideoTracks()[0];
        if (this.stream) {
            this.stream.getVideoTracks()[0].stop();
            this.stream.addTrack(newVideoTrack);
            this.stream.removeTrack(this.stream.getVideoTracks()[0]);
        }

        this.video.srcObject = this.stream;
        if (!this.isScreenSharing) {
            this._replaceVideoTrack(newVideoTrack);
        }
    }

    _replaceVideoTrack(newTrack) {
        Object.values(this.peerConnections).forEach(pc => {
            const sender = pc.getSenders().find(s => s.track?.kind === 'video');
            if (sender) sender.replaceTrack(newTrack);
        });
    }

    _broadcastAction(data) {
        if (this.currentRoomId) this._send({ type: 'meeting_action', ...data });
    }

    /**
     * CORE PIPELINE
     */
    _renderLoop() {
        if (!this.isActive) return;
        this._render();
        if (this.options.aiEnabled && !this.isProcessing) this._processFrame();
        this._renderLoopId = requestAnimationFrame(() => this._renderLoop());
    }

    _render() {
        const w = this.video.videoWidth || 640;
        const h = this.video.videoHeight || 360;
        if (this.canvas.width !== w || this.canvas.height !== h) {
            this.canvas.width = w; this.canvas.height = h;
        }
        this.ctx.save();
        if (this.options.mirrorPreview) {
            this.ctx.translate(this.canvas.width, 0);
            this.ctx.scale(-1, 1);
        }
        this.ctx.clearRect(0, 0, w, h);
        if (this.video.readyState >= 2) this.ctx.drawImage(this.video, 0, 0, w, h);
        this.ctx.restore();
    }

    async _processFrame() {
        if (!this.holistic || this.video.readyState < 2) return;
        this.isProcessing = true;
        try {
            await this.holistic.send({ image: this.video });
        } catch (e) { console.error('AI Error', e); }
        finally { this.isProcessing = false; }
    }

    _onResults(results) {
        if (this.options.showLandmarks) this._drawOverlay(results);
        if (this.socket?.readyState === WebSocket.OPEN && (results.leftHandLandmarks || results.rightHandLandmarks)) {
            this.socket.send(this._extractLandmarks(results).buffer);
        }
    }

    _drawOverlay(results) {
        this.ctx.save();
        if (this.options.mirrorPreview) {
            this.ctx.translate(this.canvas.width, 0);
            this.ctx.scale(-1, 1);
        }
        if (results.leftHandLandmarks) {
            drawConnectors(this.ctx, results.leftHandLandmarks, HAND_CONNECTIONS, { color: '#f97316', lineWidth: 3 });
        }
        if (results.rightHandLandmarks) {
            drawConnectors(this.ctx, results.rightHandLandmarks, HAND_CONNECTIONS, { color: '#fbbf24', lineWidth: 3 });
        }
        this.ctx.restore();
    }

    _extractLandmarks(results) {
        const b = new Float32Array(1662); let o = 0;
        if (results.poseLandmarks) {
            for (const l of results.poseLandmarks) { b[o++] = l.x; b[o++] = l.y; b[o++] = l.z; b[o++] = l.visibility; }
        } else o += 132;
        if (results.faceLandmarks) {
            for (const l of results.faceLandmarks) { b[o++] = l.x; b[o++] = l.y; b[o++] = l.z; }
        } else o += 1404;
        if (results.leftHandLandmarks) {
            for (const l of results.leftHandLandmarks) { b[o++] = l.x; b[o++] = l.y; b[o++] = l.z; }
        } else o += 63;
        if (results.rightHandLandmarks) {
            for (const l of results.rightHandLandmarks) { b[o++] = l.x; b[o++] = l.y; b[o++] = l.z; }
        } else o += 63;
        return b;
    }

    _send(data) { if (this.socket?.readyState === WebSocket.OPEN) this.socket.send(JSON.stringify(data)); }
    _emit(n, d) { window.dispatchEvent(new CustomEvent(n, { detail: d })); }
}
