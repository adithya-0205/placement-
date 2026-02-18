import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:provider/provider.dart';
import 'dart:convert';
import 'dart:async';
import 'package:flutter_tts/flutter_tts.dart';
import '../providers/auth_provider.dart';

class QuizScreen extends StatefulWidget {
  final String category;
  final String? targetBranch; // Added for practice mode
  const QuizScreen({super.key, required this.category, this.targetBranch});

  @override
  State<QuizScreen> createState() => _QuizScreenState();
}

class _QuizScreenState extends State<QuizScreen> {
  List<dynamic> questions = [];
  int currentIndex = 0;
  int score = 0;
  bool loading = true;
  bool showExplanation = false;
  String selectedOption = "";
  final FlutterTts flutterTts = FlutterTts();
  
  // Timer variables
  Timer? _timer;
  int _timeLeft = 300; // 5 minutes for 10 questions

  // Theme Colors
  final Color scaffoldBg = const Color(0xFF0F0C29);
  final Color cardBg = const Color(0xFF161625);
  final Color accentColor = const Color(0xFF6C63FF);

  @override
  void initState() {
    super.initState();
    _initTts();
    fetchQuestions();
  }

  void _initTts() async {
    await flutterTts.setLanguage("en-US");
    await flutterTts.setSpeechRate(0.5);
    await flutterTts.setVolume(1.0);
  }

  void _startTimer() {
    if (_timer != null) return; // Only start once
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (_timeLeft > 0) {
        if (mounted) {
          setState(() {
            _timeLeft--;
          });
        }
      } else {
        _timer?.cancel();
        _completeQuiz(); // Global time up, finish quiz
      }
    });
  }

  Future<void> _readAloud() async {
    if (questions.isNotEmpty) {
      var q = questions[currentIndex];
      String speech =
          "Question: ${q['question']}. Option A: ${q['options'][0]}. Option B: ${q['options'][1]}. Option C: ${q['options'][2]}. Option D: ${q['options'][3]}.";
      await flutterTts.speak(speech);
    }
  }

  @override
  void dispose() {
    flutterTts.stop();
    _timer?.cancel();
    super.dispose();
  }

  Future<void> fetchQuestions() async {
    final auth = Provider.of<AuthProvider>(context, listen: false);
    final url = Uri.parse('${auth.baseUrl}/get_daily_quiz');
    try {
      final res = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          "username": auth.username,
          "category": widget.category,
          "target_branch": widget.targetBranch
        }),
      );
      debugPrint("API Response: ${res.body}"); // DEBUG PRINT
      if (res.statusCode == 200) {
        if (mounted) {
          setState(() {
            questions = jsonDecode(res.body)['questions'];
            loading = false;
          });
          _readAloud();
          _startTimer();
        }
      } else {
        debugPrint("Fetch Error: ${res.statusCode} ${res.body}");
        if (mounted) {
          setState(() {
            loading = false;
          });
        } 
      }
    } catch (e) {
      debugPrint("Fetch Error: $e");
      if (mounted) {
        setState(() {
          loading = false;
        });
      }
    }
  }

  void handleAnswer(String opt) async {
    flutterTts.stop();
    // Global timer continues, do not cancel here
    
    // Set loading state for explanation if taking too long
    setState(() {
      selectedOption = opt;
    });

    final auth = Provider.of<AuthProvider>(context, listen: false);
    final url = Uri.parse('${auth.baseUrl}/check_answer');
    
    try {
      final res = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          "username": auth.username,
          "category": widget.category,
          "question_id": questions[currentIndex]['id'],
          "user_answer": opt
        }),
      );

      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        if (mounted) {
          setState(() {
            showExplanation = true;
            // Update the question's explanation with the fresh AI one
            questions[currentIndex]['explanation'] = data['explanation'];
            questions[currentIndex]['user_selected'] = opt; // Store selection
            if (data['is_correct']) score++;
          });
        }
      }
    } catch (e) {
      debugPrint("Error checking answer: $e");
      // Fallback to local check if API fails
      if (mounted) {
        setState(() {
          showExplanation = true;
          questions[currentIndex]['user_selected'] = opt; // Store selection
          if (opt == questions[currentIndex]['answer']) score++;
        });
      }
    }
  }

  void nextQuestion() async {
    if (currentIndex < questions.length - 1) {
      setState(() {
        currentIndex++;
        showExplanation = false;
        selectedOption = "";
      });
      _readAloud();
      // Global timer continues, do not reset here
    } else {
      _completeQuiz();
    }
  }

  Future<void> _completeQuiz() async {
    final auth = Provider.of<AuthProvider>(context, listen: false);
    
    // Calculate Weak Area
    Map<String, int> areaMistakes = {};
    for (int i = 0; i < questions.length; i++) {
      var q = questions[i];
      // Check if user answer matches correct answer
      // We need to store user answers. 
      // Current implementation handles scoring on per-question basis but doesn't store all user answers locally efficiently for this check unless we rely on 'score'.
      // Better approach: We know which questions were answered incorrectly if we track them.
      // But wait, 'score' is just an int. We need to track wrong answers.
    }
    
    // Let's refine the tracking.
    // We'll calculate weak area by iterating through questions and checking if the user got it right.
    // Since we don't strictly store "user_answer" in the question object in the list, we might need a separate list or update handleAnswer.
    
    // QUICK FIX: Since we want to implement this without major refactor, let's just assume we can't easily recalculate PERFECLY from current state without adding state.
    // Let's add a "user_selected" field to questions in handleAnswer.
    
    // To do this properly, I will first update handleAnswer to store the selection.
    
    String weakArea = "General";
    if (questions.isNotEmpty) {
       // Find area with most wrong answers
       for (var q in questions) {
         if (q['user_selected'] != q['answer']) {
           String area = q['area'] ?? "General";
           areaMistakes[area] = (areaMistakes[area] ?? 0) + 1;
         }
       }
       
       if (areaMistakes.isNotEmpty) {
         // Sort by count descending
         var sortedKeys = areaMistakes.keys.toList(growable: false)
            ..sort((k1, k2) => areaMistakes[k2]!.compareTo(areaMistakes[k1]!));
         weakArea = sortedKeys.first;
       }
    }

    final res = await http.post(
      Uri.parse('${auth.baseUrl}/submit_quiz'),
      headers: {"Content-Type": "application/json"},
      body: jsonEncode({
        "username": auth.username,
        "category": widget.category,
        "score": score,
        "total_questions": 10,
        "target_branch": widget.targetBranch,
        "weak_area": weakArea
      }),
    );

    bool isLevelUp = false;
    if (res.statusCode == 200) {
      isLevelUp = jsonDecode(res.body)['level_up'] ?? false;
    }

    _showResultDialog(isLevelUp, weakArea);
  }

  void _showResultDialog(bool leveledUp, String weakArea) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        backgroundColor: cardBg,
        title: Text(leveledUp ? "🎉 Level Up!" : "Quiz Over", style: const TextStyle(color: Colors.white)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
                "You scored $score/10.\n",
                style: const TextStyle(color: Colors.white70)),
            if (score < 10)
              Text(
                "Weak Area: $weakArea",
                style: const TextStyle(color: Colors.redAccent, fontWeight: FontWeight.bold),
              ),
            const SizedBox(height: 10),
            Text(
                (leveledUp 
                  ? 'You have reached a new difficulty level!' 
                  : (widget.category == "TECHNICAL" && widget.targetBranch != null) 
                    ? "Practice mode complete." 
                    : 'Try to score 7+ to level up.'),
                style: const TextStyle(color: Colors.white70)),
          ],
        ),
        actions: [
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: accentColor),
            onPressed: () => Navigator.popUntil(context, (r) => r.isFirst),
            child: const Text("Done", style: TextStyle(color: Colors.white)),
          )
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (loading) return Scaffold(backgroundColor: scaffoldBg, body: const Center(child: CircularProgressIndicator(color: Color(0xFF6C63FF))));
    if (questions.isEmpty) return Scaffold(backgroundColor: scaffoldBg, body: const Center(child: Text("No questions found.", style: TextStyle(color: Colors.white))));
    
    final q = questions[currentIndex];

    return Scaffold(
      backgroundColor: scaffoldBg,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Text("${widget.category} (Lvl ${q['difficulty']})", style: const TextStyle(color: Colors.white)),
        actions: [IconButton(icon: const Icon(Icons.volume_up, color: Colors.white70), onPressed: _readAloud)],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Styled Progress Bar
            ClipRRect(
              borderRadius: BorderRadius.circular(10),
              child: LinearProgressIndicator(
                value: (currentIndex + 1) / questions.length,
                minHeight: 8,
                backgroundColor: Colors.white10,
                color: accentColor,
              ),
            ),
            const SizedBox(height: 15),

            // Timer Display
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Icon(Icons.timer_outlined, color: _timeLeft < 30 ? Colors.redAccent : Colors.white70, size: 20),
                    const SizedBox(width: 8),
                    Text(
                      "${(_timeLeft ~/ 60).toString().padLeft(2, '0')}:${(_timeLeft % 60).toString().padLeft(2, '0')}",
                      style: TextStyle(
                        color: _timeLeft < 30 ? Colors.redAccent : Colors.white70,
                        fontWeight: FontWeight.bold,
                        fontSize: 18,
                      ),
                    ),
                  ],
                ),
                Text(
                  "Question ${currentIndex + 1} of ${questions.length}",
                  style: TextStyle(color: accentColor, fontWeight: FontWeight.bold, fontSize: 13),
                ),
              ],
            ),
            const SizedBox(height: 20),
            
            // Question Text
            Text(q['question'], style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w600, color: Colors.white)),
            
            const SizedBox(height: 35),

            // Options List
            ... (() {
              var opts = q['options'];
              List<dynamic> optionsList = [];
              if (opts is List) {
                optionsList = opts;
              } else if (opts is Map) {
                optionsList = opts.values.toList();
              }
              return optionsList;
            }()).asMap().entries.map((entry) {
              int idx = entry.key;
              String opt = entry.value;
              String optionLetter = ["A", "B", "C", "D"][idx];
              
              String correctAns = (q['answer'] ?? "").toString().trim().toUpperCase();
              String mySelected = selectedOption.trim().toUpperCase();

              bool isCorrect = optionLetter == correctAns;
              bool isSelected = optionLetter == mySelected;    

              Color btnColor = cardBg;
              Color borderCol = Colors.white12;
              
              if (showExplanation) {
                if (isCorrect) {
                  btnColor = Colors.green.withOpacity(0.2);
                  borderCol = Colors.green;
                } else if (isSelected) {
                  btnColor = Colors.red.withOpacity(0.2);
                  borderCol = Colors.red;
                }
              }

              return Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: InkWell(
                  onTap: showExplanation ? null : () => handleAnswer(optionLetter),
                  borderRadius: BorderRadius.circular(15),
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 300),
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 18),
                    decoration: BoxDecoration(
                      color: btnColor,
                      borderRadius: BorderRadius.circular(15),
                      border: Border.all(color: borderCol, width: 2),
                    ),
                    child: Text(
                      opt, 
                      style: TextStyle(
                        color: showExplanation && isCorrect ? Colors.greenAccent : Colors.white,
                        fontSize: 16,
                        fontWeight: isSelected ? FontWeight.bold : FontWeight.normal
                      )
                    ),
                  ),
                ),
              );
            }),



            // Explanation Section
            if (selectedOption != "" && !showExplanation) ...[
              const SizedBox(height: 20),
              const Center(
                child: Column(
                  children: [
                    CircularProgressIndicator(strokeWidth: 2),
                    SizedBox(height: 10),
                    Text("🤖 AI is generating explanation...", style: TextStyle(color: Colors.white70, fontStyle: FontStyle.italic)),
                  ],
                ),
              ),
            ],

            if (showExplanation) ...[
              const SizedBox(height: 20),
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.05), 
                  borderRadius: BorderRadius.circular(15),
                  border: Border.all(color: Colors.white10)
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.lightbulb_outline, color: accentColor, size: 20),
                        const SizedBox(width: 8),
                        Text("Explanation", style: TextStyle(fontWeight: FontWeight.bold, color: accentColor, fontSize: 16)),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Text(q['explanation'] ?? "Standard logic applies.", style: const TextStyle(color: Colors.white70, fontSize: 14, height: 1.5)),
                    const SizedBox(height: 25),
                    SizedBox(
                      width: double.infinity,
                      height: 50,
                      child: ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: accentColor,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))
                        ),
                        onPressed: nextQuestion, 
                        child: Text(
                          currentIndex < questions.length - 1 ? "Next Question" : "Finish Quiz",
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)
                        )
                      ),
                    )
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}