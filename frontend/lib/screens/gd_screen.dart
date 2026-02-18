import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';
import '../api_config.dart';

class GdScreen extends StatefulWidget {
  const GdScreen({super.key});

  @override
  State<GdScreen> createState() => _GdScreenState();
}

class _GdScreenState extends State<GdScreen> {
  final AudioRecorder _recorder = AudioRecorder(); // Updated to latest record API
  Map<String, dynamic>? topic;
  Map<String, dynamic>? result;

  bool loading = false;
  bool recording = false;
  int countdown = 15;
  Timer? _timer;
  String? recordedFilePath;

  // Theme Colors
  final Color scaffoldBg = const Color(0xFF0F0C29);
  final Color cardBg = const Color(0xFF1A1A2E);
  final Color accentColor = const Color(0xFF6C63FF);

  @override
  void initState() {
    super.initState();
    fetchTopic();
  }

  Future<void> fetchTopic() async {
    try {
      final data = await ApiConfig.fetchGDTopic();
      setState(() => topic = data);
    } catch (e) {
      debugPrint("Failed to fetch topic: $e");
    }
  }

  Future<void> startRecording() async {
    if (!await _recorder.hasPermission()) return;

    final dir = await getTemporaryDirectory();
    recordedFilePath = "${dir.path}/gd_${DateTime.now().millisecondsSinceEpoch}.wav";

    await _recorder.start(
      const RecordConfig(encoder: AudioEncoder.wav), 
      path: recordedFilePath!,
    );

    setState(() {
      recording = true;
      countdown = 15;
      result = null;
    });

    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (countdown == 0) {
        stopRecording();
      } else {
        setState(() => countdown--);
      }
    });
  }

  Future<void> stopRecording() async {
    _timer?.cancel();
    final path = await _recorder.stop();

    setState(() {
      recording = false;
      loading = true;
    });

    try {
      if (topic?["topic_id"] != null && path != null) {
        final res = await ApiConfig.submitGDAudio(
          topicId: topic!["topic_id"],
          audioFile: File(path),
        );
        setState(() => result = res);
      }
    } catch (e) {
      debugPrint("Submit failed: $e");
    }
    setState(() => loading = false);
  }

  @override
  void dispose() {
    _timer?.cancel();
    _recorder.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: scaffoldBg,
      appBar: AppBar(
        title: const Text("GD Module", style: TextStyle(color: Colors.white)),
        backgroundColor: Colors.transparent,
        elevation: 0,
        iconTheme: const IconThemeData(color: Colors.white),
      ),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: topic == null
            ? const Center(child: CircularProgressIndicator())
            : buildContent(),
      ),
    );
  }

  Widget buildContent() {
    return SingleChildScrollView(
      child: Column(
        children: [
          const Text("DISCUSSION TOPIC", 
            style: TextStyle(color: Colors.white54, letterSpacing: 1.2, fontSize: 12)),
          const SizedBox(height: 10),
          Text(topic!["topic"],
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 40),

          if (recording) ...[
            const BlinkingRecordingText(),
            const SizedBox(height: 10),
            Text("$countdown Seconds Remaining", style: const TextStyle(color: Colors.white70)),
          ],

          if (!recording && !loading && result == null)
            ElevatedButton.icon(
              onPressed: startRecording,
              icon: const Icon(Icons.mic),
              label: const Text("START GD SESSION"),
              style: ElevatedButton.styleFrom(
                backgroundColor: accentColor,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 30, vertical: 15),
              ),
            ),

          if (loading) const CircularProgressIndicator(),

          if (result != null) buildResultUI(),
        ],
      ),
    );
  }

  Widget buildResultUI() {
    return Container(
      margin: const EdgeInsets.only(top: 20),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(15),
        border: Border.all(color: Colors.white10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _scoreTile("Content", result!["content_score"]),
              _scoreTile("Communication", result!["communication_score"]),
            ],
          ),
          const Divider(color: Colors.white10, height: 30),
          _resultSection("Your Transcription", result!["transcript"], Colors.white70),
          _resultSection("Strict Feedback", result!["feedback"], Colors.orangeAccent),
          _resultSection("Pro Ideal Points", result!["ideal_answer"], Colors.blueAccent),
        ],
      ),
    );
  }

  Widget _scoreTile(String label, dynamic score) {
    return Column(
      children: [
        Text(label, style: const TextStyle(color: Colors.white54, fontSize: 11)),
        Text("$score/10", style: const TextStyle(color: Colors.greenAccent, fontSize: 20, fontWeight: FontWeight.bold)),
      ],
    );
  }

  Widget _resultSection(String title, String content, Color accent) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: TextStyle(color: accent, fontSize: 12, fontWeight: FontWeight.bold)),
          const SizedBox(height: 5),
          Text(content, style: const TextStyle(color: Colors.white, height: 1.4)),
        ],
      ),
    );
  }
}

class BlinkingRecordingText extends StatefulWidget {
  const BlinkingRecordingText({super.key});
  @override
  State<BlinkingRecordingText> createState() => _BlinkingRecordingTextState();
}

class _BlinkingRecordingTextState extends State<BlinkingRecordingText> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  @override
  void initState() {
    super.initState();
    _controller = AnimationController(vsync: this, duration: const Duration(seconds: 1))..repeat(reverse: true);
  }
  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }
  @override
  Widget build(BuildContext context) {
    return FadeTransition(opacity: _controller, 
      child: const Text("🔴 RECORDING LIVE", style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold, fontSize: 16)));
  }
}