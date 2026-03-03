import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:http/http.dart' as http;
import 'package:fl_chart/fl_chart.dart';
import 'dart:convert';
import 'package:url_launcher/url_launcher.dart';
import '../providers/auth_provider.dart';
import '../api_config.dart';
import 'quiz_screen.dart';
import 'interview_screen.dart'; 
import 'gd_screen.dart'; // Fixed import name to match standard file naming
import 'performance_graph.dart';
import 'leaderboard_screen.dart';
import 'dart:async';
import 'package:flutter_tts/flutter_tts.dart';
import '../widgets/branch_selection_dialog.dart';
import '../widgets/news_notification.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});
  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  Map<String, dynamic>? data;
  Map<String, dynamic>? weeklyData;
  List<dynamic>? newsData;
  bool loading = true;
  bool newsLoading = false;
  bool briefingLoading = false;
  bool isPlayingBriefing = false;
  int _selectedIndex = 0; // Tracks Sidebar selection
  bool _trendsShown = false; // Flag to show trends only once per session
  Timer? _newsTimer;
  int _currentNewsIndex = 0;
  final FlutterTts _flutterTts = FlutterTts();
  OverlayEntry? _newsOverlayEntry;

  @override
  void initState() {
    super.initState();
    loadData();
    // Use a delay to show trends popup after the UI settles
    Future.delayed(const Duration(milliseconds: 800), () {
      if (mounted) _showTrendsPopup();
    });
    _loadNews().then((_) => _startNewsTimer());
  }

  @override
  void dispose() {
    _newsTimer?.cancel();
    _newsOverlayEntry?.remove();
    _newsOverlayEntry = null;
    super.dispose();
  }

  void _startNewsTimer() {
    _newsTimer = Timer.periodic(const Duration(minutes: 5), (timer) {
      if (newsData != null && newsData!.isNotEmpty) {
        _showNewsNotification(newsData![_currentNewsIndex]);
        _currentNewsIndex = (_currentNewsIndex + 1) % newsData!.length;
      }
    });
  }

  void _showNewsNotification(dynamic item) {
    if (_newsOverlayEntry != null) {
      _newsOverlayEntry?.remove();
      _newsOverlayEntry = null;
    }

    _newsOverlayEntry = OverlayEntry(
      builder: (context) => Positioned(
        top: 50,
        right: 0,
        child: NewsNotification(
          item: item,
          onDismiss: () {
            _newsOverlayEntry?.remove();
            _newsOverlayEntry = null;
          },
          onRead: (text) async {
            await _flutterTts.setLanguage("en-US");
            await _flutterTts.setPitch(1.0);
            await _flutterTts.speak(text);
          },
        ),
      ),
    );

    Overlay.of(context).insert(_newsOverlayEntry!);

    // Automatically dismiss after 15 seconds
    Future.delayed(const Duration(seconds: 15), () {
      if (_newsOverlayEntry != null) {
        _newsOverlayEntry?.remove();
        _newsOverlayEntry = null;
      }
    });
  }

  Future<void> loadData() async {
    final auth = Provider.of<AuthProvider>(context, listen: false);
    try {
      final res1 = await http.get(Uri.parse('${auth.baseUrl}/dashboard/${auth.username}'));
      final res2 = await http.get(Uri.parse('${auth.baseUrl}/weekly_report/${auth.username}'));

      if (res1.statusCode == 200) {
        setState(() {
          data = jsonDecode(res1.body);
          if (res2.statusCode == 200) weeklyData = jsonDecode(res2.body);
          loading = false;
        });
      }
    } catch (e) {
      debugPrint(e.toString());
      setState(() => loading = false);
    }
  }

  Future<void> _loadNews() async {
    if (newsData != null) return; // Only load once or if forced
    setState(() => newsLoading = true);
    try {
      final news = await ApiConfig.fetchLatestNews();
      setState(() {
        newsData = news;
        newsLoading = false;
      });
    } catch (e) {
      debugPrint("NEWS ERROR: $e");
      setState(() => newsLoading = false);
    }
  }

  Future<void> _playIndustryBriefing() async {
    if (isPlayingBriefing) {
      await _flutterTts.stop();
      setState(() => isPlayingBriefing = false);
      return;
    }

    setState(() => briefingLoading = true);
    try {
      final briefing = await ApiConfig.fetchIndustryTrendsBriefing();
      setState(() {
        briefingLoading = false;
        isPlayingBriefing = true;
      });
      await _flutterTts.setLanguage("en-US");
      await _flutterTts.speak(briefing);

      _flutterTts.setCompletionHandler(() {
        if (mounted) {
          setState(() => isPlayingBriefing = false);
        }
      });
    } catch (e) {
      debugPrint("Briefing ERROR: $e");
      setState(() {
        briefingLoading = false;
        isPlayingBriefing = false;
      });
    }
  }

  Widget _buildDashboardSection(AuthProvider auth) {
    if (data == null) return const Center(child: CircularProgressIndicator());

    return SingleChildScrollView(
      padding: const EdgeInsets.all(32),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildTopSection(auth),
          const SizedBox(height: 32),
          _buildAchievementsSection(),
          const SizedBox(height: 32),
          _buildMiddleSection(context),
          const SizedBox(height: 32),
          _buildFocusAreas(),
          const SizedBox(height: 32),
          _buildBottomSection(),
        ],
      ),
    );
  }

  // --- TOP SECTION: Level & Weekly Progress ---
  Widget _buildTopSection(AuthProvider auth) {
    double progress = (data?['weekly_progress'] ?? 0.0) / 100.0;
    
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: const LinearGradient(colors: [Color(0xFF6366F1), Color(0xFFA855F7)]),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [BoxShadow(color: Colors.purple.withOpacity(0.3), blurRadius: 20, offset: const Offset(0, 10))],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text("Current Level", style: TextStyle(color: Colors.white70, fontSize: 14)),
                  Text("Level ${data?['technical_level'] ?? 1}", style: const TextStyle(color: Colors.white, fontSize: 28, fontWeight: FontWeight.bold)),
                ],
              ),
              const Icon(Icons.stars, color: Colors.white, size: 40),
            ],
          ),
          const SizedBox(height: 20),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text("Weekly Progress", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
              Text("${(progress * 100).toInt()}%", style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
            ],
          ),
          const SizedBox(height: 10),
          ClipRRect(
            borderRadius: BorderRadius.circular(10),
            child: LinearProgressIndicator(
              value: progress,
              backgroundColor: Colors.white24,
              color: Colors.white,
              minHeight: 12,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAchievementsSection() {
    final badges = weeklyData?['badges'] ?? [];
    if (badges.isEmpty) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text("Your Achievements", style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold)),
        const SizedBox(height: 16),
        SizedBox(
          height: 100,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: badges.length,
            separatorBuilder: (context, index) => const SizedBox(width: 16),
            itemBuilder: (context, index) {
              final badge = badges[index];
              return _badgeItem(badge['name'], badge['icon'], _getBadgeColor(badge['color']));
            },
          ),
        ),
      ],
    );
  }

  Color _getBadgeColor(String colorName) {
    switch (colorName) {
      case 'gold': return Colors.amber;
      case 'orange': return Colors.orangeAccent;
      case 'blue': return Colors.blueAccent;
      case 'purple': return Colors.purpleAccent;
      default: return Colors.grey;
    }
  }

  Widget _badgeItem(String label, String iconName, Color color) {
    IconData iconData;
    switch (iconName) {
      case 'emoji_events': iconData = Icons.emoji_events; break;
      case 'whatshot': iconData = Icons.whatshot; break;
      case 'record_voice_over': iconData = Icons.record_voice_over; break;
      case 'face': iconData = Icons.face; break;
      default: iconData = Icons.stars;
    }

    return Container(
      width: 100,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF161625),
        borderRadius: BorderRadius.circular(15),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(iconData, color: color, size: 30),
          const SizedBox(height: 8),
          Text(
            label,
            textAlign: TextAlign.center,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
          ),
        ],
      ),
    );
  }

  // --- MIDDLE SECTION: Today's Tasks ---
  Widget _buildMiddleSection(BuildContext context) {
    final tasks = data?['tasks'] ?? {};
    bool aptDone = tasks['aptitude_done'] ?? false;
    bool techDone = tasks['tech_done'] ?? false;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text("Today's Practice", style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold)),
        const SizedBox(height: 16),
        Row(
          children: [
            _taskItem("Aptitude (10 questions)", aptDone, Colors.orangeAccent, () => _startQuiz(context, "APTITUDE")),
            const SizedBox(width: 20),
            _taskItem("Technical (10 questions)", techDone, Colors.blueAccent, () => _startQuiz(context, "TECHNICAL")),
          ],
        ),
      ],
    );
  }

  Widget _taskItem(String label, bool isDone, Color color, VoidCallback onTap) {
    return Expanded(
      child: InkWell(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: const Color(0xFF161625),
            borderRadius: BorderRadius.circular(15),
            border: Border.all(color: isDone ? color : Colors.white10),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(color: color.withOpacity(0.1), shape: BoxShape.circle),
                child: Icon(isDone ? Icons.check : Icons.play_arrow, color: color),
              ),
              const SizedBox(width: 15),
              Expanded(child: Text(label, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold))),
              if (isDone) const Icon(Icons.verified, color: Colors.greenAccent, size: 20),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildFocusAreas() {
    List techWeak = data?['weak_areas_tech'] ?? [];
    List aptWeak = data?['weak_areas_apt'] ?? [];
    String techStatus = data?['weak_areas_tech_status'] ?? "active";
    String aptStatus = data?['weak_areas_apt_status'] ?? "active";
    
    // Status overrules list content for UI messaging
    bool isCollecting = (techStatus == "collecting" || aptStatus == "collecting");

    int techLvl = data?['technical_level'] ?? 1;
    int aptLvl = data?['aptitude_level'] ?? 1;

    String getLvlName(int l) {
      if (l == 1) return "Easy";
      if (l == 2) return "Medium";
      if (l == 3) return "Hard";
      return "Company-level";
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text("Focus Areas", style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold)),
        const SizedBox(height: 16),
        if (isCollecting)
           Container(
             width: double.infinity,
             padding: const EdgeInsets.all(20),
             decoration: BoxDecoration(color: const Color(0xFF161625), borderRadius: BorderRadius.circular(15), border: Border.all(color: Colors.white10)),
             child: const Row(
               children: [
                 Icon(Icons.insights, color: Colors.purpleAccent),
                 SizedBox(width: 15),
                 Expanded(
                   child: Text(
                     "Collecting daily performance data to identify your focus areas. Keep practicing!",
                     style: TextStyle(color: Colors.white70, fontSize: 13, fontStyle: FontStyle.italic),
                   ),
                 ),
               ],
             ),
           )
        else
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _focusCard("Technical", techWeak, Colors.blueAccent, getLvlName(techLvl)),
              const SizedBox(width: 20),
              _focusCard("Aptitude", aptWeak, Colors.orangeAccent, getLvlName(aptLvl)),
            ],
          ),
      ],
    );
  }

  Widget _focusCard(String title, List areas, Color color, String level) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(color: const Color(0xFF161625), borderRadius: BorderRadius.circular(15)),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(title, style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 16)),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(color: color.withOpacity(0.1), borderRadius: BorderRadius.circular(8)),
                  child: Text(level, style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.bold)),
                ),
              ],
            ),
            const SizedBox(height: 15),
            if (areas.isEmpty)
              const Text("Great job! No weak areas found.", style: TextStyle(color: Colors.white38, fontSize: 12, fontStyle: FontStyle.italic))
            else
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: areas.map((a) {
                  final areaName = a is Map ? (a['area'] ?? "None") : a.toString();
                  return Container(
                    margin: const EdgeInsets.only(bottom: 8),
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.05),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: Colors.white10)
                    ),
                    child: Text(
                      areaName,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 13,
                        fontWeight: FontWeight.w500
                      ),
                    ),
                  );
                }).toList(),
              ),
          ],
        ),
      ),
    );
  }

  Widget _countTag(String text, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withOpacity(0.2)),
      ),
      child: Text(
        text,
        style: TextStyle(color: color, fontSize: 9, fontWeight: FontWeight.bold),
      ),
    );
  }

  // --- BOTTOM SECTION: Graphs & Reports ---
  Widget _buildBottomSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text("Performance Report", style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold)),
            TextButton(
              onPressed: () {
                Navigator.push(context, MaterialPageRoute(builder: (context) => PerformanceGraph()));
              },
              child: const Text("View Full Analytics", style: TextStyle(color: Colors.purpleAccent)),
            )
          ],
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            _miniStat("Total Attempted", "${data?['total_attempts'] ?? 0}", Icons.assignment_outlined, Colors.cyanAccent),
            _miniStat("Avg Accuracy", "${data?['accuracy'] ?? 0}%", Icons.track_changes, Colors.greenAccent),
          ],
        ),
        const SizedBox(height: 24),
        _buildGraphSection(),
        const SizedBox(height: 24),
        _buildTopicAccuracySection(),
      ],
    );
  }

  Widget _miniStat(String label, String value, IconData icon, Color color) {
    return Expanded(
      child: Container(
        margin: const EdgeInsets.only(right: 15),
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(color: const Color(0xFF161625), borderRadius: BorderRadius.circular(15)),
        child: Row(
          children: [
            Icon(icon, color: color, size: 24),
            const SizedBox(width: 15),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(value, style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
                Text(label, style: const TextStyle(color: Colors.white38, fontSize: 12)),
              ],
            )
          ],
        ),
      ),
    );
  }

  Widget _buildNewsSection() {
    return Padding(
      padding: const EdgeInsets.all(32),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text("Industry Trends", style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Colors.white)),
                  Text("Latest updates from Hacker News", style: TextStyle(color: Colors.white54)),
                ],
              ),
              IconButton(
                icon: const Icon(Icons.refresh, color: Colors.purpleAccent),
                onPressed: () {
                  setState(() => newsData = null);
                  _loadNews();
                },
              ),
            ],
          ),
          const SizedBox(height: 16),
          _buildBriefingBanner(),
          const SizedBox(height: 20),
          Expanded(
            child: newsLoading
                ? const Center(child: CircularProgressIndicator(color: Colors.purpleAccent))
                : newsData == null || newsData!.isEmpty
                    ? const Center(child: Text("No trends found", style: TextStyle(color: Colors.white38)))
                    : ListView.builder(
                        itemCount: newsData!.length,
                        itemBuilder: (context, index) {
                          final item = newsData![index];
                          return _buildNewsCard(item);
                        },
                      ),
          ),
        ],
      ),
    );
  }

  Widget _buildBriefingBanner() {
    return InkWell(
      onTap: briefingLoading ? null : _playIndustryBriefing,
      borderRadius: BorderRadius.circular(15),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 15),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [Colors.purpleAccent.withOpacity(0.2), Colors.indigo.withOpacity(0.2)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(15),
          border: Border.all(color: Colors.purpleAccent.withOpacity(0.5)),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: Colors.purpleAccent.withOpacity(0.2),
                shape: BoxShape.circle,
              ),
              child: briefingLoading 
                ? const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(color: Colors.purpleAccent, strokeWidth: 2))
                : Icon(
                    isPlayingBriefing ? Icons.stop_circle_outlined : Icons.multitrack_audio, 
                    color: Colors.purpleAccent, 
                    size: 24
                  ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    isPlayingBriefing ? "Playing Briefing..." : "Listen to Industry AI Briefing",
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
                  ),
                  const Text(
                    "A personalized 3-sentence summary of current trends.",
                    style: TextStyle(color: Colors.white54, fontSize: 12),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildNewsCard(dynamic item) {
    return _newsCardItem(item);
  }

  Widget _newsCardItem(dynamic item, {bool isPopup = false}) {
    return Card(
      color: isPopup ? Colors.white.withOpacity(0.08) : Colors.white.withOpacity(0.05),
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15)),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        title: Text(item['title'] ?? 'No Title', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: isPopup ? 14 : 16)),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 4.0),
          child: Text(
            "Points: ${item['score']} • By: ${item['by']}",
            style: const TextStyle(color: Colors.white38, fontSize: 11),
          ),
        ),
        onTap: () async {
          final url = Uri.parse(item['url']);
          if (await canLaunchUrl(url)) {
            await launchUrl(url, mode: LaunchMode.externalApplication);
          }
        },
      ),
    );
  }

  void _showTrendsPopup() async {
    if (_trendsShown) return;
    _trendsShown = true;

    showDialog(
      context: context,
      builder: (context) => _TrendsDialog(),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (loading) return const Scaffold(backgroundColor: Color(0xFF0F0C29), body: Center(child: CircularProgressIndicator()));
    
    final auth = Provider.of<AuthProvider>(context);
    const Color sidebarBg = Color(0xFF161625);
    const Color scaffoldBg = Color(0xFF0F0C29);

    return Scaffold(
      backgroundColor: scaffoldBg,
      body: Row(
        children: [
          // --- SIDEBAR (Left Panel) ---
          Container(
            width: 280,
            color: sidebarBg,
            child: Column(
              children: [
                const SizedBox(height: 40),
                _buildSidebarHeader(),
                const SizedBox(height: 20),
                
                _buildProfileCard(auth.username ?? "User"),
                
                const SizedBox(height: 30),
                _sidebarTile(0, Icons.dashboard_outlined, "Dashboard"),
                _sidebarTile(1, Icons.code, "Technical Practice", onTap: () => _startQuiz(context, "TECHNICAL")),
                _sidebarTile(2, Icons.psychology_outlined, "Aptitude Practice", onTap: () => _startQuiz(context, "APTITUDE")),
                
                // FIXED ERROR HERE: Removed any internal 'const' that could conflict with Navigator
                _sidebarTile(3, Icons.groups_outlined, "GD Practice", onTap: () {
                  Navigator.push(context, MaterialPageRoute(builder: (_) => const GdScreen()));
                }),
                
                _sidebarTile(4, Icons.mic_none, "Interview Practice", onTap: () {  
                   Navigator.push(context, MaterialPageRoute(builder: (_) => const InterviewScreen()));
                }),

                _sidebarTile(5, Icons.auto_graph, "Industry Trends", onTap: () {
                  setState(() => _selectedIndex = 5);
                  _loadNews();
                }),

                _sidebarTile(6, Icons.workspace_premium_outlined, "Wall of Fame", onTap: () {
                  Navigator.push(context, MaterialPageRoute(builder: (_) => const LeaderboardScreen()));
                }),

                const Spacer(),
                _sidebarTile(-1, Icons.logout, "Logout", onTap: () => Navigator.pop(context)),
                const SizedBox(height: 20),
              ],
            ),
          ),

          // --- MAIN CONTENT AREA ---
          Expanded(
            child: _selectedIndex == 5 
                ? _buildNewsSection()
                : _buildDashboardSection(auth),
          ),
        ],
      ),
    );
  }

  // --- UI COMPONENTS ---

  Widget _buildSidebarHeader() {
    return const Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Icon(Icons.auto_awesome, color: Colors.purpleAccent),
        SizedBox(width: 10),
        Text("AI Placement", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 18)),
      ],
    );
  }

  Widget _buildProfileCard(String name) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20),
      padding: const EdgeInsets.all(15),
      decoration: BoxDecoration(color: Colors.white.withOpacity(0.05), borderRadius: BorderRadius.circular(15)),
      child: Row(
        children: [
          const CircleAvatar(backgroundColor: Colors.blueAccent, child: Icon(Icons.person, color: Colors.white)),
          const SizedBox(width: 12),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(name, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
              Text("${data?['branch'] ?? 'Set Branch'} • Student", style: const TextStyle(color: Colors.white38, fontSize: 11)),
            ],
          )
        ],
      ),
    );
  }

  Widget _sidebarTile(int index, IconData icon, String label, {VoidCallback? onTap, bool isComingSoon = false}) {
    bool isSelected = _selectedIndex == index;
    return ListTile(
      onTap: isComingSoon ? null : (onTap ?? () => setState(() => _selectedIndex = index)),
      leading: Icon(icon, color: isSelected ? Colors.purpleAccent : Colors.white54),
      title: Text(label, style: TextStyle(color: isSelected ? Colors.white : Colors.white54, fontSize: 14)),
      trailing: isComingSoon ? Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        decoration: BoxDecoration(color: Colors.white10, borderRadius: BorderRadius.circular(5)),
        child: const Text("Soon", style: TextStyle(color: Colors.white38, fontSize: 10)),
      ) : null,
    );
  }

  Widget _statCard(String label, String value, IconData icon, Color color) {
    return Expanded(
      child: Container(
        margin: const EdgeInsets.only(right: 15),
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(color: const Color(0xFF161625), borderRadius: BorderRadius.circular(20)),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: color, size: 28),
            const SizedBox(height: 15),
            Text(value, style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Colors.white)),
            Text(label, style: const TextStyle(color: Colors.white38, fontSize: 12)),
          ],
        ),
      ),
    );
  }

  Widget _buildGraphSection() {
    List<FlSpot> aptSpots = [];
    List<FlSpot> techSpots = [];
    
    if (weeklyData != null && weeklyData!['has_data'] == true) {
      final aptData = weeklyData!['aptitude_daily'] as List;
      final techData = weeklyData!['technical_daily'] as List;
      
      for (int i = 0; i < aptData.length; i++) {
        aptSpots.add(FlSpot(i.toDouble(), double.tryParse(aptData[i]['score'].toString()) ?? 0));
      }
      for (int i = 0; i < techData.length; i++) {
        techSpots.add(FlSpot(i.toDouble(), double.tryParse(techData[i]['score'].toString()) ?? 0));
      }
    }

    if (aptSpots.isEmpty) aptSpots = [const FlSpot(0, 0), const FlSpot(6, 0)];
    if (techSpots.isEmpty) techSpots = [const FlSpot(0, 0), const FlSpot(6, 0)];

    return Container(
      height: 300,
      padding: const EdgeInsets.all(25),
      decoration: BoxDecoration(color: const Color(0xFF161625), borderRadius: BorderRadius.circular(20)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text("Performance Trends (Last 7 Days)", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
              Row(
                children: [
                  _legendItem("Aptitude", Colors.blueAccent),
                  const SizedBox(width: 15),
                  _legendItem("Technical", Colors.cyanAccent),
                ],
              )
            ],
          ),
          const SizedBox(height: 20),
          Expanded(
            child: LineChart(
              LineChartData(
                minY: 0,
                maxY: 10,
                gridData: FlGridData(
                  show: true,
                  drawVerticalLine: false,
                  getDrawingHorizontalLine: (value) => const FlLine(color: Colors.white10, strokeWidth: 1),
                ),
                titlesData: FlTitlesData(
                  topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      getTitlesWidget: (value, meta) {
                        int index = value.toInt();
                        if (weeklyData?['has_data'] == true) {
                          final aptData = weeklyData!['aptitude_daily'] as List;
                          if (index >= 0 && index < aptData.length) {
                             String time = aptData[index]['time']?.toString() ?? "";
                             if (time.length >= 10) {
                               return Text(
                                 time.substring(5, 10), // MM-DD
                                 style: const TextStyle(color: Colors.white38, fontSize: 10)
                               );
                             }
                          }
                        }
                        return const Text("");
                      },
                    ),
                  ),
                ),
                borderData: FlBorderData(show: false),
                lineBarsData: [
                  LineChartBarData(
                    spots: aptSpots,
                    isCurved: true,
                    color: Colors.blueAccent,
                    barWidth: 3,
                    dotData: const FlDotData(show: true),
                    belowBarData: BarAreaData(show: true, color: Colors.blueAccent.withOpacity(0.05)),
                  ),
                  LineChartBarData(
                    spots: techSpots,
                    isCurved: true,
                    color: Colors.cyanAccent,
                    barWidth: 3,
                    dotData: const FlDotData(show: true),
                    belowBarData: BarAreaData(show: true, color: Colors.cyanAccent.withOpacity(0.05)),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _legendItem(String label, Color color) {
    return Row(
      children: [
        Container(width: 12, height: 12, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
        const SizedBox(width: 5),
        Text(label, style: const TextStyle(color: Colors.white70, fontSize: 11)),
      ],
    );
  }


  Widget _buildTopicAccuracySection() {
    double gdScore = 0;
    double interviewScore = 0;
    
    if (weeklyData != null) {
      final gdList = weeklyData!['gd_weekly'] as List?;
      final invList = weeklyData!['interview_weekly'] as List?;
      
      if (gdList != null && gdList.isNotEmpty) {
        gdScore = (double.tryParse(gdList.last['score'].toString()) ?? 0) / 10;
      }
      if (invList != null && invList.isNotEmpty) {
        interviewScore = (double.tryParse(invList.last['score'].toString()) ?? 0) / 10;
      }
    }

    return Container(
      padding: const EdgeInsets.all(25),
      decoration: BoxDecoration(color: const Color(0xFF161625), borderRadius: BorderRadius.circular(20)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text("Weekly Session Highlights", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
          const SizedBox(height: 20),
          _topicBar("GD Performance (Last Session)", gdScore, Colors.orangeAccent),
          _topicBar("Interview Confidence (Last Session)", interviewScore, Colors.greenAccent),
        ],
      ),
    );
  }

  Widget _topicBar(String label, double val, Color color) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 15),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(color: Colors.white70, fontSize: 12)),
          const SizedBox(height: 8),
          LinearProgressIndicator(value: val, backgroundColor: Colors.white10, color: color, minHeight: 8),
        ],
      ),
    );
  }

  void _startQuiz(BuildContext context, String cat) async {
    // For Technical quiz, show branch selection first (Practice Mode)
    if (cat == "TECHNICAL") {
      final selectedBranch = await showDialog<String>(
        context: context,
        barrierDismissible: false,
        builder: (_) => BranchSelectionDialog(initialBranch: data?['branch'], practiceMode: true),
      );
      
      if (selectedBranch != null && context.mounted) {
        Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => QuizScreen(category: cat, targetBranch: selectedBranch)),
        ).then((_) => loadData());
      }
    } else {
      // For Aptitude, start directly
      Navigator.push(
        context,
        MaterialPageRoute(builder: (_) => QuizScreen(category: cat)),
      ).then((_) => loadData());
    }
  }

  void _showBranchSelection() {
    showDialog(
      context: context,
      barrierDismissible: false, // Force them to choose
      builder: (_) => BranchSelectionDialog(initialBranch: data?['branch']),
    ).then((selected) {
      if (selected != null) {
        loadData(); // Reload to get updated branch
      }
    });
  }
}

class _TrendsDialog extends StatefulWidget {
  @override
  State<_TrendsDialog> createState() => _TrendsDialogState();
}

class _TrendsDialogState extends State<_TrendsDialog> {
  List<dynamic>? trends;
  bool loading = true;
  final FlutterTts _flutterTts = FlutterTts();

  @override
  void initState() {
    super.initState();
    _fetchTrends();
  }

  Future<void> _fetchTrends() async {
    try {
      final data = await ApiConfig.fetchLatestNews();
      if (mounted) {
        setState(() {
          trends = data;
          loading = false;
        });
      }
    } catch (e) {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: const Color(0xFF161625),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(25)),
      child: Container(
        width: 500,
        height: 600,
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text("Industry Trends", style: TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.bold)),
                    Text("Stay updated with the latest tech news", style: TextStyle(color: Colors.white38, fontSize: 12)),
                  ],
                ),
                IconButton(
                  icon: const Icon(Icons.close, color: Colors.white54),
                  onPressed: () => Navigator.pop(context),
                ),
              ],
            ),
            const SizedBox(height: 20),
            Expanded(
              child: loading
                  ? const Center(child: CircularProgressIndicator(color: Colors.purpleAccent))
                  : trends == null || trends!.isEmpty
                      ? const Center(child: Text("No trending topics found", style: TextStyle(color: Colors.white38)))
                      : ListView.builder(
                          itemCount: trends!.length,
                          itemBuilder: (context, index) {
                            final item = trends![index];
                            return _buildPopupNewsCard(item);
                          },
                        ),
            ),
            const SizedBox(height: 15),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.purpleAccent,
                  padding: const EdgeInsets.symmetric(vertical: 15),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                onPressed: () => Navigator.pop(context),
                child: const Text("Got it!", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPopupNewsCard(dynamic item) {
    return Card(
      color: Colors.white.withOpacity(0.05),
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15)),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        title: Text(item['title'] ?? 'No Title', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13)),
        trailing: IconButton(
          icon: const Icon(Icons.volume_up, color: Colors.purpleAccent, size: 18),
          onPressed: () async {
             final summary = await ApiConfig.fetchNewsSummary(item['title'] ?? '');
             await _flutterTts.setLanguage("en-US");
             await _flutterTts.speak(summary);
          },
        ),
        onTap: () async {
          final url = Uri.parse(item['url']);
          if (await canLaunchUrl(url)) {
            await launchUrl(url, mode: LaunchMode.externalApplication);
          }
        },
      ),
    );
  }
}