import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:ui';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';

class PerformanceGraph extends StatefulWidget {
  @override
  _PerformanceGraphState createState() => _PerformanceGraphState();
}

class _PerformanceGraphState extends State<PerformanceGraph> {
  Map<String, dynamic> reportData = {};
  Map<String, dynamic> dashboardData = {};
  bool isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    final auth = Provider.of<AuthProvider>(context, listen: false);
    final String username = auth.username ?? "Student";

    try {
      final reportRes = await http.get(Uri.parse('${auth.baseUrl}/weekly_report/$username'));
      final dashRes = await http.get(Uri.parse('${auth.baseUrl}/dashboard/$username'));

      if (reportRes.statusCode == 200 && dashRes.statusCode == 200) {
        setState(() {
          reportData = json.decode(reportRes.body);
          dashboardData = json.decode(dashRes.body);
          isLoading = false;
        });
      }
    } catch (e) {
      print("Error fetching graph data: $e");
      setState(() => isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (isLoading) return const Scaffold(backgroundColor: Color(0xFF0F172A), body: Center(child: CircularProgressIndicator(color: Colors.indigoAccent)));

    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      body: Stack(
        children: [
          // Background Glows
          Positioned(top: -100, right: -50, child: _blurGlow(Colors.indigo.withOpacity(0.2), 300)),
          Positioned(bottom: 100, left: -50, child: _blurGlow(Colors.purple.withOpacity(0.15), 250)),
          
          CustomScrollView(
            slivers: [
              _buildAppBar(),
              SliverPadding(
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                sliver: SliverList(
                  delegate: SliverChildListDelegate([
                    _buildReadinessHero(),
                    const SizedBox(height: 24),
                    _buildQuickStats(),
                    const SizedBox(height: 32),
                    _sectionHeader("Daily Momentum", "Performance trends over the last 7 sessions"),
                    const SizedBox(height: 16),
                    _buildDailyChart(),
                    const SizedBox(height: 32),
                    _sectionHeader("Skill Profile", "Areas where you excel and areas for growth"),
                    const SizedBox(height: 16),
                    _buildSkillProfile(),
                    const SizedBox(height: 32),
                    _sectionHeader("Mastery Wall", "Your collection of earned placement badges"),
                    const SizedBox(height: 16),
                    _buildMasteryWall(),
                    const SizedBox(height: 32),
                    _sectionHeader("Weekly Growth", "Success in GD & Interviews over the month"),
                    const SizedBox(height: 16),
                    _buildWeeklyChart(),
                    const SizedBox(height: 40),
                  ]),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildAppBar() {
    return SliverAppBar(
      backgroundColor: Colors.transparent,
      elevation: 0,
      expandedHeight: 80,
      floating: true,
      centerTitle: false,
      title: const Text("Full Analytics", style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 24)),
      iconTheme: const IconThemeData(color: Colors.white),
    );
  }

  Widget _sectionHeader(String title, String sub) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
        const SizedBox(height: 4),
        Text(sub, style: const TextStyle(color: Colors.white38, fontSize: 12)),
      ],
    );
  }

  Widget _buildReadinessHero() {
    double readiness = (reportData['readiness_score'] ?? 0.0).toDouble();
    String status = reportData['status'] ?? "Preparing";

    return _glassCard(
      padding: const EdgeInsets.all(24),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text("Placement Readiness", style: TextStyle(color: Colors.white60, fontSize: 14)),
                const SizedBox(height: 8),
                Text(status, style: const TextStyle(color: Colors.white, fontSize: 32, fontWeight: FontWeight.w900)),
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(color: Colors.indigoAccent.withOpacity(0.2), borderRadius: BorderRadius.circular(20)),
                  child: const Text("Keep grinding to level up!", style: TextStyle(color: Colors.indigoAccent, fontSize: 11, fontWeight: FontWeight.bold)),
                ),
              ],
            ),
          ),
          Stack(
            alignment: Alignment.center,
            children: [
              SizedBox(
                width: 90,
                height: 90,
                child: CircularProgressIndicator(
                  value: readiness / 100,
                  strokeWidth: 10,
                  backgroundColor: Colors.white.withOpacity(0.1),
                  color: readiness > 75 ? Colors.greenAccent : (readiness > 40 ? Colors.indigoAccent : Colors.orangeAccent),
                ),
              ),
              Text("${readiness.toInt()}%", style: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w900)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildQuickStats() {
    return Row(
      children: [
        _statItem("Attempts", "${dashboardData['total_attempts'] ?? 0}", Icons.auto_graph, Colors.cyanAccent),
        const SizedBox(width: 12),
        _statItem("Accuracy", "${dashboardData['accuracy'] ?? 0}%", Icons.track_changes, Colors.greenAccent),
        const SizedBox(width: 12),
        _statItem("Streak", "${reportData['streak'] ?? 0}d", Icons.whatshot, Colors.orangeAccent),
      ],
    );
  }

  Widget _statItem(String label, String value, IconData icon, Color color) {
    return Expanded(
      child: _glassCard(
        padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 12),
        child: Column(
          children: [
            Icon(icon, color: color.withOpacity(0.8), size: 18),
            const SizedBox(height: 8),
            Text(value, style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 2),
            Text(label, style: const TextStyle(color: Colors.white38, fontSize: 10)),
          ],
        ),
      ),
    );
  }

  Widget _buildDailyChart() {
    List<FlSpot> aptSpots = _getSpots(reportData['aptitude_daily']);
    List<FlSpot> techSpots = _getSpots(reportData['technical_daily']);

    return _glassCard(
      padding: const EdgeInsets.fromLTRB(10, 24, 20, 16),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              _legendItem("Aptitude", Colors.indigoAccent),
              const SizedBox(width: 20),
              _legendItem("Technical", Colors.greenAccent),
            ],
          ),
          const SizedBox(height: 24),
          SizedBox(
            height: 200,
            child: LineChart(
              LineChartData(
                gridData: FlGridData(show: true, drawVerticalLine: false, getDrawingHorizontalLine: (v) => FlLine(color: Colors.white.withOpacity(0.05), strokeWidth: 1)),
                titlesData: _chartTitles(),
                borderData: FlBorderData(show: false),
                lineBarsData: [
                  _lineData(aptSpots, Colors.indigoAccent),
                  _lineData(techSpots, Colors.greenAccent),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSkillProfile() {
    final strong = reportData['strong_areas'] ?? [];
    final needsFocus = (dashboardData['weak_areas_tech'] ?? []) + (dashboardData['weak_areas_apt'] ?? []);

    return Column(
      children: [
        _skillBlock("Top Strengths", strong, Colors.greenAccent),
        const SizedBox(height: 16),
        _skillBlock("Growth Areas", needsFocus, Colors.orangeAccent),
      ],
    );
  }

  Widget _skillBlock(String title, List items, Color color) {
    return _glassCard(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(width: 4, height: 16, decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(2))),
              const SizedBox(width: 8),
              Text(title, style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold)),
            ],
          ),
          const SizedBox(height: 16),
          if (items.isEmpty)
             const Text("Keep practicing to unlock insights...", style: TextStyle(color: Colors.white24, fontSize: 12, fontStyle: FontStyle.italic))
          else
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: items.map((i) {
                String label = i is Map ? i['area'].toString() : i.toString();
                return Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(color: color.withOpacity(0.1), borderRadius: BorderRadius.circular(8), border: Border.all(color: color.withOpacity(0.2))),
                  child: Text(label, style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w600)),
                );
              }).toList(),
            ),
        ],
      ),
    );
  }

  Widget _buildMasteryWall() {
    final badges = reportData['badges'] ?? [];
    if (badges.isEmpty) return _glassCard(padding: const EdgeInsets.all(20), child: const Text("Unlock your first badge by mastering a topic!", style: TextStyle(color: Colors.white24, fontSize: 13, fontStyle: FontStyle.italic)));

    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount: 3, crossAxisSpacing: 12, mainAxisSpacing: 12, childAspectRatio: 0.9),
      itemCount: badges.length,
      itemBuilder: (context, index) {
        final badge = badges[index];
        return _glassCard(
          padding: const EdgeInsets.all(12),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(_badgeIcon(badge['icon']), color: _getBadgeColor(badge['color']), size: 32),
              const SizedBox(height: 8),
              Text(badge['name'], textAlign: TextAlign.center, style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold)),
            ],
          ),
        );
      },
    );
  }

  IconData _badgeIcon(String name) {
    switch (name) {
      case 'emoji_events': return Icons.emoji_events;
      case 'whatshot': return Icons.whatshot;
      case 'record_voice_over': return Icons.record_voice_over;
      case 'face': return Icons.face;
      default: return Icons.stars;
    }
  }

  Color _getBadgeColor(String name) {
    switch (name) {
      case 'gold': return Colors.amber;
      case 'orange': return Colors.orangeAccent;
      case 'blue': return Colors.blueAccent;
      case 'purple': return Colors.purpleAccent;
      default: return Colors.indigoAccent;
    }
  }

  Widget _buildWeeklyChart() {
    return _glassCard(
      padding: const EdgeInsets.all(20),
      child: SizedBox(
        height: 180,
        child: BarChart(
          BarChartData(
            gridData: const FlGridData(show: false),
            titlesData: _barTitles(),
            borderData: FlBorderData(show: false),
            barGroups: _getBarGroups(),
          ),
        ),
      ),
    );
  }

  // --- Helpers ---
  Widget _glassCard({required Widget child, EdgeInsetsGeometry? padding}) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(24),
      child: Container(
        padding: padding,
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.03),
          borderRadius: BorderRadius.circular(24),
          border: Border.all(color: Colors.white.withOpacity(0.08)),
        ),
        child: child,
      ),
    );
  }

  Widget _blurGlow(Color color, double size) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(color: color, shape: BoxShape.circle),
      child: BackdropFilter(filter: ImageFilter.blur(sigmaX: 80, sigmaY: 80), child: Container(color: Colors.transparent)),
    );
  }

  Widget _legendItem(String label, Color color) {
    return Row(
      children: [
        Container(width: 10, height: 10, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
        const SizedBox(width: 8),
        Text(label, style: const TextStyle(color: Colors.white54, fontSize: 11, fontWeight: FontWeight.bold)),
      ],
    );
  }

  List<FlSpot> _getSpots(List? data) {
    if (data == null || data.isEmpty) return [const FlSpot(0, 0)];
    return List.generate(data.length, (i) => FlSpot(i.toDouble(), (data[i]['score'] as num).toDouble()));
  }

  LineChartBarData _lineData(List<FlSpot> spots, Color color) {
    return LineChartBarData(
      spots: spots,
      isCurved: true,
      color: color,
      barWidth: 4,
      isStrokeCapRound: true,
      dotData: FlDotData(show: true, getDotPainter: (s, p, b, i) => FlDotCirclePainter(radius: 4, color: color, strokeWidth: 2, strokeColor: Colors.white)),
      belowBarData: BarAreaData(show: true, gradient: LinearGradient(begin: Alignment.topCenter, end: Alignment.bottomCenter, colors: [color.withOpacity(0.2), color.withOpacity(0.01)])),
    );
  }

  FlTitlesData _chartTitles() {
    return FlTitlesData(
      leftTitles: AxisTitles(sideTitles: SideTitles(showTitles: true, reservedSize: 25, getTitlesWidget: (v, m) => Text(v.toInt().toString(), style: const TextStyle(color: Colors.white24, fontSize: 10)))),
      bottomTitles: AxisTitles(sideTitles: SideTitles(showTitles: true, getTitlesWidget: (v, m) => Text("S${v.toInt() + 1}", style: const TextStyle(color: Colors.white24, fontSize: 10)))),
      rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
      topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
    );
  }

  FlTitlesData _barTitles() {
    return FlTitlesData(
      leftTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
      bottomTitles: AxisTitles(sideTitles: SideTitles(showTitles: true, getTitlesWidget: (v, m) => Text("Week ${v.toInt() + 1}", style: const TextStyle(color: Colors.white24, fontSize: 10)))),
      rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
      topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
    );
  }

  List<BarChartGroupData> _getBarGroups() {
    List gd = reportData['gd_weekly'] ?? [];
    List interview = reportData['interview_weekly'] ?? [];
    int len = gd.length > interview.length ? gd.length : interview.length;
    if (len == 0) return [];

    return List.generate(len, (i) {
      double gdScore = i < gd.length ? (gd[i]['score'] as num).toDouble() : 0;
      double intScore = i < interview.length ? (interview[i]['score'] as num).toDouble() : 0;
      return BarChartGroupData(
        x: i,
        barRods: [
          BarChartRodData(toY: gdScore, color: Colors.orangeAccent, width: 10, borderRadius: BorderRadius.circular(4)),
          BarChartRodData(toY: intScore, color: Colors.pinkAccent, width: 10, borderRadius: BorderRadius.circular(4)),
        ],
      );
    });
  }
}
