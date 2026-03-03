import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:record/record.dart';
import 'package:http/http.dart' as http;
import 'package:provider/provider.dart';
import 'package:path_provider/path_provider.dart';
import '../providers/auth_provider.dart';

class InterviewScreen extends StatefulWidget {
  const InterviewScreen({super.key});
  @override
  State<InterviewScreen> createState() => _InterviewScreenState();
}

class _InterviewScreenState extends State<InterviewScreen> with WidgetsBindingObserver {
  CameraController? _camera;
  final AudioRecorder _recorder = AudioRecorder();
  List<dynamic> _questions = [];
  int _currentIndex = 0;
  int _secondsLeft = 30;
  Timer? _timer;
  Timer? _frameTimer;
  bool _isLoading = false;
  Map<String, dynamic>? _result;
  String? _liveWarning = "INITIALIZING";
  String? _cameraError;
  bool _screenWarning = false;
  bool _isTestStarted = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _startSession();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused || state == AppLifecycleState.inactive || state == AppLifecycleState.hidden) {
      if (!_isLoading && _result == null) {
        setState(() => _screenWarning = true);
        Future.delayed(const Duration(seconds: 4), () {
          if (mounted) setState(() => _screenWarning = false);
        });
      }
    }
  }

  Future<void> _startSession() async {
    try {
      final cams = await availableCameras();
      if (cams.isEmpty) {
        setState(() => _cameraError = "No camera found. Please connect a webcam.");
        return;
      }
      
      _camera = CameraController(
        cams[0], 
        ResolutionPreset.low,
        enableAudio: false,
      );
      
      await _camera!.initialize();
      if (mounted) setState(() => _cameraError = null);
    } catch (e) {
      if (mounted) {
        setState(() {
          _cameraError = "Camera Error: Please ensure no other app is using the webcam.";
          print("Camera Init Error: $e");
        });
      }
    }
    
    try {
      final auth = Provider.of<AuthProvider>(context, listen: false);
      final response = await http.get(Uri.parse('${auth.baseUrl}/get_questions/${auth.username}/TECHNICAL'));
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (mounted) {
          setState(() {
            _questions = data['questions'];
            _currentIndex = 0; 
          });
        }
        if (_cameraError == null) _startLiveFrameAnalysis();
      }
    } catch (e) {
      print("Error fetching questions: $e");
    }
  }

  void _beginInterview() {
    setState(() {
      _isTestStarted = true;
    });
    _startQuestionTimer();
  }

  void _startLiveFrameAnalysis() {
    _frameTimer = Timer.periodic(const Duration(milliseconds: 1500), (timer) async {
      if (_camera == null || !_camera!.value.isInitialized || _isLoading) return;
      if (_camera!.value.isTakingPicture) return;
      
      try {
        final xFile = await _camera!.takePicture();
        final auth = Provider.of<AuthProvider>(context, listen: false);
        var req = http.MultipartRequest('POST', Uri.parse('${auth.baseUrl}/process_frame'));
        req.fields['username'] = auth.username!;
        req.files.add(await http.MultipartFile.fromPath('frame', xFile.path));
        
        final res = await req.send();
        if (res.statusCode == 200) {
          final body = await http.Response.fromStream(res);
          final data = jsonDecode(body.body);
          if (mounted) {
            setState(() {
              _liveWarning = data['warning'];
            });
          }
        }
        // Cleanup temp file to avoid filling up disk
        File(xFile.path).delete().catchError((e) => null);
      } catch (e) {
        // Ignore frame dropping errors
      }
    });
  }

  void _startQuestionTimer() async {
    setState(() => _secondsLeft = 30);
    final path = (await getTemporaryDirectory()).path;
    await _recorder.start(const RecordConfig(), path: '$path/q_$_currentIndex.m4a');

    _timer = Timer.periodic(const Duration(seconds: 1), (t) {
      if (_secondsLeft > 0) {
        setState(() => _secondsLeft--);
      } else {
        _timer?.cancel();
        _nextOrSubmit();
      }
    });
  }

  void _nextOrSubmit() async {
    final path = await _recorder.stop();
    final auth = Provider.of<AuthProvider>(context, listen: false);
    
    if (_questions.isEmpty || _currentIndex >= _questions.length) return;

    var stepReq = http.MultipartRequest('POST', Uri.parse('${auth.baseUrl}/evaluate_step'));
    stepReq.fields['username'] = auth.username!;
    stepReq.fields['question'] = _questions[_currentIndex]['question'];
    stepReq.fields['index'] = _currentIndex.toString();
    stepReq.files.add(await http.MultipartFile.fromPath('audio', path!));
    await stepReq.send();

    if (_currentIndex < _questions.length - 1) {
      setState(() {
        _currentIndex++;
      });
      _startQuestionTimer();
    } else {
      _uploadFinalData();
    }
  }

  Future<void> _uploadFinalData() async {
    setState(() {
      _isLoading = true;
      _liveWarning = null;
    });
    _frameTimer?.cancel();
    
    final auth = Provider.of<AuthProvider>(context, listen: false);
    // Request final report directly, no video needed!
    var req = http.MultipartRequest('POST', Uri.parse('${auth.baseUrl}/final_session_report'));
    req.fields['username'] = auth.username!;
    
    var res = await req.send();
    var body = await http.Response.fromStream(res);
    setState(() {
      _result = jsonDecode(body.body);
      _isLoading = false;
    });
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _timer?.cancel();
    _frameTimer?.cancel();
    _camera?.dispose();
    _recorder.dispose();
    super.dispose();
  }

  String _getWarningMessage() {
    if (_screenWarning) return "⚠️  WARNING: Screen change detected! Stay on this screen.";
    switch (_liveWarning) {
      case "INITIALIZING": return "🔄 Initializing Camera... Please wait.";
      case "FACE_NOT_DETECTED": return "🤷 Face not detected! Move into view.";
      case "OUT_OF_BOX": return "📦 Face out of frame! Center yourself.";
      case "EYE_GAZE": return "👀 Looking away! Maintain eye contact.";
      default: return "";
    }
  }

  Color _getWarningColor() {
    if (_screenWarning) return Colors.redAccent.shade700;
    switch (_liveWarning) {
      case "INITIALIZING": return Colors.blueAccent;
      case "FACE_NOT_DETECTED": return Colors.red;
      case "OUT_OF_BOX": return Colors.orange;
      case "EYE_GAZE": return Colors.amber.shade700;
      default: return Colors.transparent;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new, color: Colors.white, size: 20),
          onPressed: () => Navigator.pop(context),
        ),
        title: const Text("AI Interview", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
        centerTitle: true,
      ),
      body: Container(
        color: const Color(0xFF0F0C29), // Match main app Scaffold background
        child: SafeArea(
          child: _isLoading 
            ? _buildLoadingView()
            : _result != null ? _buildReportView() : _buildInterviewView(),
        ),
      ),
    );
  }

  Widget _buildLoadingView() {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          CircularProgressIndicator(color: Colors.cyanAccent),
          SizedBox(height: 25),
          Text(
            "Analyzing Behavior & Technical Accuracy...", 
            style: TextStyle(color: Colors.white70, fontSize: 16, fontWeight: FontWeight.w500)
          )
        ],
      )
    );
  }

  Widget _buildInterviewView() {
    if (_questions.isEmpty) {
      return const Center(child: CircularProgressIndicator(color: Colors.cyanAccent));
    }

    final warningMsg = _getWarningMessage();
    final hasWarning = warningMsg.isNotEmpty;

    if (_cameraError != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(30.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.videocam_off, color: Colors.redAccent, size: 64),
              const SizedBox(height: 20),
              Text(
                _cameraError!,
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.white, fontSize: 16),
              ),
              const SizedBox(height: 30),
              ElevatedButton(
                onPressed: _startSession,
                style: ElevatedButton.styleFrom(backgroundColor: Colors.cyanAccent),
                child: const Text("Retry Connection", style: TextStyle(color: Colors.black)),
              )
            ],
          ),
        ),
      );
    }

    return Column(
      children: [
        // Camera Preview with Modern Styling
        if (_camera != null && _camera!.value.isInitialized)
          Expanded(
            flex: 5,
            child: Container(
              margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(24),
                boxShadow: [
                  BoxShadow(color: hasWarning ? _getWarningColor().withOpacity(0.5) : Colors.cyanAccent.withOpacity(0.1), blurRadius: 20, spreadRadius: 2)
                ],
                border: Border.all(
                  color: hasWarning ? _getWarningColor() : Colors.white12, 
                  width: hasWarning ? 3 : 1
                )
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(24),
                child: Stack(
                  fit: StackFit.expand,
                  children: [
                    CameraPreview(_camera!),
                    // Live Warning Overlay
                    if (hasWarning)
                      Positioned(
                        top: 20,
                        left: 20,
                        right: 20,
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(12),
                          child: BackdropFilter(
                            filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
                            child: Container(
                              padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
                              color: _getWarningColor().withOpacity(0.8),
                              child: Row(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Expanded(
                                    child: Text(
                                      warningMsg, 
                                      textAlign: TextAlign.center,
                                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ),
          ),
          
        // Question & Control Card OR Pre-Interview Card
        Expanded(
          flex: 4,
          child: Container(
            margin: const EdgeInsets.fromLTRB(20, 10, 20, 20),
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: const Color(0xFF161625), // Matched card color
              borderRadius: BorderRadius.circular(30),
            ),
            child: _isTestStarted 
              ? Column(
                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text("Question ${_currentIndex + 1}/${_questions.length}", 
                          style: const TextStyle(color: Colors.cyanAccent, fontWeight: FontWeight.w600, fontSize: 14)),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                          decoration: BoxDecoration(
                            color: _secondsLeft < 10 ? Colors.redAccent.withOpacity(0.2) : Colors.greenAccent.withOpacity(0.2),
                            borderRadius: BorderRadius.circular(20)
                          ),
                          child: Row(
                            children: [
                              Icon(Icons.timer, size: 16, color: _secondsLeft < 10 ? Colors.redAccent : Colors.greenAccent),
                              const SizedBox(width: 6),
                              Text(
                                "00:${_secondsLeft.toString().padLeft(2, '0')}", 
                                style: TextStyle(
                                  color: _secondsLeft < 10 ? Colors.redAccent : Colors.greenAccent, 
                                  fontWeight: FontWeight.bold
                                )
                              ),
                            ],
                          ),
                        )
                      ],
                    ),
                    
                    Text(
                      _questions[_currentIndex]['question'],
                      textAlign: TextAlign.center, 
                      style: const TextStyle(color: Colors.white, fontSize: 18, height: 1.4, fontWeight: FontWeight.w500),
                    ),
                    
                    // Audio Wave Animation Placeholder
                    Container(
                      height: 60,
                      width: double.infinity,
                      decoration: BoxDecoration(
                        color: Colors.black12,
                        borderRadius: BorderRadius.circular(30)
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.mic, 
                            color: _secondsLeft % 2 == 0 ? Colors.cyanAccent : Colors.white54, 
                            size: 28
                          ),
                          const SizedBox(width: 15),
                          const Text("Recording Answer...", style: TextStyle(color: Colors.white54, fontSize: 14, letterSpacing: 1.2)),
                        ],
                      ),
                    ),
                  ],
                )
              : Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Text(
                      "Pre-Interview Check",
                      style: TextStyle(color: Colors.cyanAccent, fontSize: 24, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 20),
                    const Text(
                      "Please ensure your face is clearly visible, centered in the camera, and maintain eye contact to begin.",
                      textAlign: TextAlign.center,
                      style: TextStyle(color: Colors.white70, fontSize: 16, height: 1.5),
                    ),
                    const SizedBox(height: 30),
                    SizedBox(
                      width: double.infinity,
                      height: 55,
                      child: ElevatedButton(
                        onPressed: hasWarning ? null : _beginInterview,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.cyanAccent.withOpacity(0.8),
                          disabledBackgroundColor: Colors.grey.withOpacity(0.3),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                        ),
                        child: Text(
                          hasWarning ? "Fix Warnings to Start" : "Start Interview",
                          style: TextStyle(
                            color: hasWarning ? Colors.white54 : Colors.black,
                            fontSize: 18,
                            fontWeight: FontWeight.bold
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
          ),
        ),
      ],
    );
  }

  Widget _buildReportView() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 40),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.05),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: Colors.cyanAccent.withOpacity(0.3))
              ),
              child: Column(
                children: [
                  const Text("Final Score", style: TextStyle(color: Colors.white54, fontSize: 16)),
                  const SizedBox(height: 5),
                  Text("${_result!['final_score']}", style: const TextStyle(color: Colors.cyanAccent, fontSize: 36, fontWeight: FontWeight.bold)),
                ],
              ),
            ),
          ),
          const SizedBox(height: 30),
          
          _buildFeedbackSection("Confidence & Demeanor", _result!['overall_confidence'], Icons.person),
          const SizedBox(height: 20),
          _buildFeedbackSection("Behavioral Feedback", _result!['behavioral_feedback'], Icons.remove_red_eye),
          
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 20),
            child: Divider(color: Colors.white24, height: 1),
          ),
          
          const Text("Detailed Breakdown", style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold)),
          const SizedBox(height: 20),
          
          ...(_result!['technical_report'] as List).map((item) => Container(
            margin: const EdgeInsets.only(bottom: 20),
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.05),
              borderRadius: BorderRadius.circular(16)
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text("Q: ${item['question']}", style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 15)),
                const SizedBox(height: 12),
                _buildResponseRow("Accuracy:", item['accuracy'] ?? "N/A", Colors.cyanAccent),
                const SizedBox(height: 8),
                _buildResponseRow("Your Answer:", item['your_answer'], Colors.white70),
                const SizedBox(height: 8),
                _buildResponseRow("Ideal Answer:", item['ideal_answer'], Colors.greenAccent.shade200),
                const SizedBox(height: 8),
                _buildResponseRow("Key Improvement:", item['improvement'], Colors.orangeAccent),
              ],
            ),
          )).toList(),
        ],
      ),
    );
  }

  Widget _buildResponseRow(String label, String text, Color color) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(width: 120, child: Text(label, style: TextStyle(color: color.withOpacity(0.7), fontSize: 13, fontWeight: FontWeight.w500))),
        Expanded(child: Text(text, style: TextStyle(color: color, fontSize: 14, height: 1.3))),
      ],
    );
  }
  
  Widget _buildFeedbackSection(String title, String content, IconData icon) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, color: Colors.cyanAccent, size: 20),
            const SizedBox(width: 10),
            Text(title, style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600)),
          ],
        ),
        const SizedBox(height: 10),
        Text(content, style: const TextStyle(color: Colors.white70, fontSize: 15, height: 1.4)),
      ],
    );
  }
}