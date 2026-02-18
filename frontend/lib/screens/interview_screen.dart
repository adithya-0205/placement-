import 'package:flutter/material.dart';
import 'package:record/record.dart';
import 'package:http/http.dart' as http;
import 'package:provider/provider.dart';
import 'package:path_provider/path_provider.dart';
import 'dart:convert';
// ignore: unsupported_import
import 'dart:io' show File;
import '../providers/auth_provider.dart';

class InterviewScreen extends StatefulWidget {
  const InterviewScreen({super.key});

  @override
  State<InterviewScreen> createState() => _InterviewScreenState();
}

class _InterviewScreenState extends State<InterviewScreen> {
  final AudioRecorder _recorder = AudioRecorder();
  bool _isRecording = false;
  bool _isLoading = false;
  Map<String, dynamic>? _result;

  final Color scaffoldBg = const Color(0xFF0F0C29);
  final Color accentColor = const Color(0xFF6C63FF);

  @override
  void dispose() {
    _recorder.dispose();
    super.dispose();
  }

  Future<void> _toggleRecording() async {
    try {
      if (_isRecording) {
        final path = await _recorder.stop();
        setState(() => _isRecording = false);
        if (path != null) {
          _sendToServer(path);
        }
      } else {
        if (await _recorder.hasPermission()) {
          final tempDir = await getTemporaryDirectory();
          final String filePath = '${tempDir.path}\\interview_audio.m4a';

          const config = RecordConfig(
            encoder: AudioEncoder.aacLc, 
            bitRate: 128000,
            sampleRate: 44100,
          );

          await _recorder.start(config, path: filePath);
          setState(() => _isRecording = true);
        }
      }
    } catch (e) {
      debugPrint("Recording Error: $e");
    }
  }

  Future<void> _sendToServer(String path) async {
    setState(() {
      _isLoading = true;
      _result = null;
    });
    
    final auth = Provider.of<AuthProvider>(context, listen: false);
    
    try {
      var request = http.MultipartRequest('POST', Uri.parse('${auth.baseUrl}/evaluate_interview'));
      request.files.add(await http.MultipartFile.fromPath('audio', path));
      request.fields['username'] = auth.username ?? "Anonymous";


      var streamedResponse = await request.send();
      var response = await http.Response.fromStream(streamedResponse);
      
      if (response.statusCode == 200) {
        setState(() {
          _result = json.decode(response.body);
        });
      }
    } catch (e) {
      debugPrint("Upload Error: $e");
    } finally {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: scaffoldBg,
      appBar: AppBar(
        title: const Text("AI Interviewer", style: TextStyle(color: Colors.white)),
        backgroundColor: Colors.transparent,
        elevation: 0,
        iconTheme: const IconThemeData(color: Colors.white), 
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Text("Topic: Explain final vs const in Dart", 
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
              const SizedBox(height: 15),
              if (_isRecording)
                const Text("🔴 RECORDING LIVE", style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold)),
              const SizedBox(height: 40),
              
              GestureDetector(
                onTap: _isLoading ? null : _toggleRecording,
                child: CircleAvatar(
                  radius: 50,
                  backgroundColor: _isRecording ? Colors.red : accentColor,
                  child: Icon(_isRecording ? Icons.stop : Icons.mic, size: 40, color: Colors.white),
                ),
              ),
              const SizedBox(height: 20),
              
              if (_isLoading) const CircularProgressIndicator(),

              if (_result != null) _buildResultCard(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildResultCard() {
  return Container(
    margin: const EdgeInsets.only(top: 20),
    padding: const EdgeInsets.all(20),
    decoration: BoxDecoration(
      color: const Color(0xFF1A1A2E), 
      borderRadius: BorderRadius.circular(15),
      border: Border.all(color: Colors.white10),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Center(
          child: Text(
            "SCORE: ${_result!['score']}",
            style: TextStyle(
              color: (_result!['score'].toString().contains('0') || _result!['score'].toString().contains('1')) 
                  ? Colors.redAccent : Colors.greenAccent,
              fontSize: 22,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        const SizedBox(height: 20),
        
        const Text("WHAT YOU SAID:", style: TextStyle(color: Colors.white38, fontSize: 10, fontWeight: FontWeight.bold)),
        Text("\"${_result!['transcription']}\"", style: const TextStyle(color: Colors.white70, fontStyle: FontStyle.italic)),
        
        const Divider(color: Colors.white10, height: 30),
        
        const Text("INTERVIEWER FEEDBACK", style: TextStyle(color: Colors.orangeAccent, fontSize: 12, fontWeight: FontWeight.bold)),
        const SizedBox(height: 5),
        Text("${_result!['feedback']}", style: const TextStyle(color: Colors.white, height: 1.4)),
        
        const SizedBox(height: 25),
        
        // Detailed Ideal Answer Section
        const Text("PRO-LEVEL IDEAL ANSWER", style: TextStyle(color: Colors.blueAccent, fontSize: 12, fontWeight: FontWeight.bold)),
        const SizedBox(height: 10),
        Container(
          padding: const EdgeInsets.all(15),
          decoration: BoxDecoration(
            color: Colors.blueAccent.withOpacity(0.1),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: Colors.blueAccent.withOpacity(0.3)),
          ),
          child: Text(
            "${_result!['ideal_answer']}",
            style: const TextStyle(color: Colors.white70, fontSize: 13, height: 1.5),
          ),
        ),
      ],
    ),
  );
}
}