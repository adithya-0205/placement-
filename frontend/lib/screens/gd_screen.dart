import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';
import '../api_config.dart';

class GdScreen extends StatefulWidget {
  const GdScreen({super.key});

  @override
  State<GdScreen> createState() => _GdScreenState();
}

class _GdScreenState extends State<GdScreen> with WidgetsBindingObserver {
  CameraController? _cameraController;
  final AudioRecorder _audioRecorder = AudioRecorder();

  bool _cameraInitialized = false;
  bool _recording = false;
  bool _loading = false;
  bool _isDisposed = false;
  int _countdown = 15;
  Timer? _timer;

  Map<String, dynamic>? topic;
  Map<String, dynamic>? result;
  String? _error;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _initializeSystem();
  }

  // Handle app lifecycle (Minimizing/Restoring)
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (_isDisposed || _cameraController == null) return;

    // On Windows, aggressive disposal on inactive can lead to crashes
    // We only react if the app is explicitly resumed and the camera was lost
    if (state == AppLifecycleState.resumed && !_cameraInitialized) {
      _initCamera();
    }
  }

  Future<void> _initializeSystem() async {
    await fetchTopic();
    await _initCamera();
  }

  Future<void> _initCamera() async {
    if (_isDisposed || !mounted) return;

    // Properly dispose old controller before creating new one
    if (_cameraController != null) {
      await _cameraController!.dispose();
      _cameraController = null;
      if (mounted) setState(() => _cameraInitialized = false);
    }

    setState(() => _error = null);

    try {
      final cameras = await availableCameras();
      if (cameras.isEmpty) {
        if (mounted) setState(() => _error = "No cameras found.");
        return;
      }

      final frontCamera = cameras.firstWhere(
        (cam) => cam.lensDirection == CameraLensDirection.front,
        orElse: () => cameras.first,
      );

      final controller = CameraController(
        frontCamera,
        ResolutionPreset.medium,
        enableAudio: false, // Prevent audio conflict with 'record' package
      );

      _cameraController = controller;
      await controller.initialize();

      if (!_isDisposed && mounted) {
        setState(() => _cameraInitialized = true);
      }
    } catch (e) {
      debugPrint("Camera init error: $e");
      if (!_isDisposed && mounted) {
        setState(() => _error = "Camera error: ${e.toString().split('\n').first}");
      }
    }
  }

  Future<void> fetchTopic() async {
    try {
      final data = await ApiConfig.fetchGDTopic();
      if (!_isDisposed) setState(() => topic = data);
    } catch (e) {
      debugPrint("Topic fetch error: $e");
    }
  }

  Future<void> startSession() async {
    if (_cameraController == null || !_cameraController!.value.isInitialized || _recording) return;

    try {
      // 0. Ensure previous recording is stopped
      if (_cameraController!.value.isRecordingVideo) {
        await _cameraController!.stopVideoRecording();
      }

      // 1. Start Video
      await _cameraController!.startVideoRecording();

      // 2. Start Audio
      final dir = await getTemporaryDirectory();
      final audioPath =
          "${dir.path}/gd_audio_${DateTime.now().millisecondsSinceEpoch}.wav";

      await _audioRecorder.start(
        const RecordConfig(encoder: AudioEncoder.wav),
        path: audioPath,
      );

      setState(() {
        _recording = true;
        _countdown = 15;
        result = null;
      });

      _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
        if (_countdown == 0) {
          stopSession(audioPath);
        } else {
          setState(() => _countdown--);
        }
      });
    } catch (e) {
      debugPrint("Start session error: $e");
    }
  }

  Future<void> stopSession(String aPath) async {
    _timer?.cancel();
    if (_isDisposed) return;

    setState(() {
      _recording = false;
      _loading = true;
    });

    try {
      final XFile videoFile = await _cameraController!.stopVideoRecording();
      final String? audioPath = await _audioRecorder.stop();

      if (topic?["topic_id"] != null && audioPath != null) {
        final res = await ApiConfig.submitGD(
          topicId: topic!["topic_id"],
          audioFile: File(audioPath),
          videoFile: File(videoFile.path),
        );
        if (!_isDisposed) setState(() => result = res);
      }
    } catch (e) {
      debugPrint("Submit error: $e");
    } finally {
      if (!_isDisposed) setState(() => _loading = false);
    }
  }

  @override
  void dispose() {
    _isDisposed = true;
    WidgetsBinding.instance.removeObserver(this);
    _timer?.cancel();
    _cameraController?.dispose();
    _audioRecorder.dispose();
    super.dispose();
  }

  // ================= UI SECTION =================
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F0C29),
      appBar: AppBar(
          title: const Text("GD Module"),
          backgroundColor: Colors.transparent,
          elevation: 0),
      body: topic == null
          ? const Center(child: CircularProgressIndicator())
          : _buildLayout(),
    );
  }

  Widget _buildLayout() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        children: [
          Text("TOPIC: ${topic!["topic"]}",
              style: const TextStyle(
                  color: Colors.white,
                  fontSize: 18,
                  fontWeight: FontWeight.bold),
              textAlign: TextAlign.center),
          const SizedBox(height: 30),
          _buildCameraPreview(),
          const SizedBox(height: 30),
          _buildControls(),
          if (result != null) _buildResultUI(),
        ],
      ),
    );
  }

  Widget _buildCameraPreview() {
    return AspectRatio(
      aspectRatio: 16 / 9,
      child: Container(
        decoration: BoxDecoration(
          color: Colors.black,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white10),
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(15),
          child: (_cameraInitialized && _cameraController != null && _cameraController!.value.isInitialized)
              ? CameraPreview(_cameraController!)
              : _error != null
                  ? Center(
                      child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(_error!,
                            style: const TextStyle(color: Colors.white70)),
                        TextButton(
                            onPressed: _initCamera,
                            child: const Text("Retry Camera"))
                      ],
                    ))
                  : const Center(
                      child: CircularProgressIndicator(color: Colors.white)),
        ),
      ),
    );
  }

  Widget _buildControls() {
    if (_loading) return const CircularProgressIndicator();

    if (_recording) {
      return Column(
        children: [
          const Text("🔴 RECORDING LIVE",
              style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold)),
          Text("$_countdown Seconds",
              style: const TextStyle(color: Colors.white)),
        ],
      );
    }

    return ElevatedButton.icon(
      icon: const Icon(Icons.videocam),
      label: const Text("START GD EVALUATION"),
      onPressed: _cameraInitialized ? startSession : null,
      style: ElevatedButton.styleFrom(
        backgroundColor: const Color(0xFF6C63FF),
        padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 15),
      ),
    );
  }

  Widget _buildResultUI() {
    return Container(
      margin: const EdgeInsets.only(top: 30),
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: const Color(0xFF1A1A2E), // Your cardBg
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white10),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.3),
            blurRadius: 10,
            offset: const Offset(0, 5),
          )
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // --- SCORE DASHBOARD ---
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _scoreTile("Final Score", result!["final_score"],
                  const Color(0xFF6C63FF)),
              _scoreTile(
                  "Content", result!["content_score"], Colors.greenAccent),
              _scoreTile(
                  "Confidence", result!["camera_score"], Colors.orangeAccent),
            ],
          ),
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 20),
            child: Divider(color: Colors.white10, thickness: 1),
          ),

          // --- FEEDBACK SECTION ---
          _sectionHeader(Icons.analytics_outlined, "AI Performance Feedback",
              Colors.orangeAccent),
          const SizedBox(height: 12),
          Text(
            result!["feedback"] ?? "No feedback available.",
            style: const TextStyle(
                color: Colors.white70, fontSize: 14, height: 1.5),
          ),

          const SizedBox(height: 25),

          // --- IDEAL ANSWER SECTION ---
          _sectionHeader(
              Icons.auto_awesome, "Suggested Ideal Answer", Colors.blueAccent),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.blueAccent.withOpacity(0.05),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.blueAccent.withOpacity(0.2)),
            ),
            child: Text(
              result!["ideal_answer"] ?? "Generating suggested response...",
              style: const TextStyle(
                color: Colors.white,
                fontSize: 14,
                fontStyle: FontStyle.italic,
                height: 1.5,
              ),
            ),
          ),

          const SizedBox(height: 30),

          // --- ACTION BUTTON ---
          Center(
            child: TextButton.icon(
              onPressed: () => setState(() => result = null),
              icon: const Icon(Icons.refresh, color: Colors.white70),
              label: const Text("TRY ANOTHER TOPIC",
                  style: TextStyle(
                      color: Colors.white70, fontWeight: FontWeight.bold)),
            ),
          ),
        ],
      ),
    );
  }

  // --- UI HELPERS ---

  Widget _scoreTile(String label, dynamic score, Color color) {
    return Column(
      children: [
        Text(label,
            style: const TextStyle(color: Colors.white54, fontSize: 12)),
        const SizedBox(height: 8),
        Stack(
          alignment: Alignment.center,
          children: [
            SizedBox(
              height: 60,
              width: 60,
              child: CircularProgressIndicator(
                value: (double.tryParse(score.toString()) ?? 0) / 10,
                backgroundColor: Colors.white10,
                color: color,
                strokeWidth: 6,
              ),
            ),
            Text(
              "$score",
              style: const TextStyle(
                  color: Colors.white,
                  fontSize: 18,
                  fontWeight: FontWeight.bold),
            ),
          ],
        ),
      ],
    );
  }

  Widget _sectionHeader(IconData icon, String title, Color color) {
    return Row(
      children: [
        Icon(icon, color: color, size: 20),
        const SizedBox(width: 10),
        Text(
          title.toUpperCase(),
          style: TextStyle(
              color: color,
              fontSize: 13,
              fontWeight: FontWeight.bold,
              letterSpacing: 1.2),
        ),
      ],
    );
  }
}