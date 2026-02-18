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
import '../widgets/branch_selection_dialog.dart';

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
  int _selectedIndex = 0; // Tracks Sidebar selection
  bool _trendsShown = false; // Flag to show trends only once per session

  @override
  void initState() {
    super.initState();
    loadData();
    // Use a delay to show trends popup after the UI settles
    Future.delayed(const Duration(milliseconds: 800), () {
      if (mounted) _showTrendsPopup();
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

  Widget _buildDashboardSection(AuthProvider auth) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(32),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            "Good Evening, ${auth.username}!", 
            style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Colors.white)
          ),
          const Text(
            "Let's continue your placement preparation journey", 
            style: TextStyle(color: Colors.white54)
          ),
          const SizedBox(height: 32),

          Row(
            children: [
              _statCard("Current Level", "${data?['technical_level'] ?? 0}", Icons.emoji_events_outlined, Colors.purpleAccent),
              _statCard("Tech Weakness", "${data?['weak_area_tech'] ?? 'None'}", Icons.code, Colors.redAccent),
              _statCard("Apt Weakness", "${data?['weak_area_apt'] ?? 'None'}", Icons.calculate_outlined, Colors.orangeAccent),
              _statCard("Points", "2736", Icons.military_tech_outlined, Colors.deepPurpleAccent),
            ],
          ),

          const SizedBox(height: 32),
          _buildGraphSection(),
          const SizedBox(height: 32),
          _buildTopicAccuracySection(),
        ],
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
          const SizedBox(height: 30),
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
        trailing: Icon(Icons.open_in_new, color: Colors.purpleAccent.withOpacity(0.7), size: 18),
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
    List<FlSpot> spots = [];
    if (weeklyData != null && weeklyData!['has_data'] == true) {
      final graphData = weeklyData!['graph_data'] as List;
      for (int i = 0; i < graphData.length; i++) {
        spots.add(FlSpot(i.toDouble(), double.tryParse(graphData[i]['score'].toString()) ?? 0));
      }
    } else {
      // Fallback/Placeholder if no data
      spots = [const FlSpot(0, 0), const FlSpot(6, 0)];
    }

    return Container(
      height: 300,
      padding: const EdgeInsets.all(25),
      decoration: BoxDecoration(color: const Color(0xFF161625), borderRadius: BorderRadius.circular(20)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text("Weekly Holistic Growth", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
          Text(
            weeklyData?['has_data'] == true 
              ? "Historical performance across all modules" 
              : "Complete your first week for historical tracking", 
            style: const TextStyle(color: Colors.white38, fontSize: 12)
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
                          final graphData = weeklyData!['graph_data'] as List;
                          if (index < graphData.length) {
                             // Show date or week number
                             return Text(
                               graphData[index]['time'].toString().substring(5), // MM-DD
                               style: const TextStyle(color: Colors.white38, fontSize: 10)
                             );
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
                    spots: spots,
                    isCurved: true,
                    color: Colors.cyanAccent,
                    barWidth: 4,
                    dotData: const FlDotData(show: true),
                    belowBarData: BarAreaData(show: true, color: Colors.cyanAccent.withOpacity(0.1)),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }


  Widget _buildTopicAccuracySection() {
    return Container(
      padding: const EdgeInsets.all(25),
      decoration: BoxDecoration(color: const Color(0xFF161625), borderRadius: BorderRadius.circular(20)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text("Topic-wise Accuracy", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
          const SizedBox(height: 20),
          _topicBar("Aptitude", 0.75, Colors.blue),
          _topicBar("Technical", 0.85, Colors.green),
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
        trailing: const Icon(Icons.open_in_new, color: Colors.purpleAccent, size: 18),
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