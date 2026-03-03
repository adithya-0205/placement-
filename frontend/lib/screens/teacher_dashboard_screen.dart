import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../services/teacher_api_service.dart';
import 'student_detail_screen.dart';

class TeacherDashboardScreen extends StatefulWidget {
  final String teacherName;

  const TeacherDashboardScreen({
    Key? key,
    required this.teacherName,
  }) : super(key: key);

  @override
  _TeacherDashboardScreenState createState() => _TeacherDashboardScreenState();
}

class _TeacherDashboardScreenState extends State<TeacherDashboardScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final Color backgroundColor = const Color(0xFF0A0E21);
  final Color cardColor = const Color(0xFF1D1E33);
  final Color accentColor = const Color(0xFF24D876);

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Theme(
      data: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: backgroundColor,
        primaryColor: accentColor,
        cardTheme: CardThemeData(
          color: cardColor,
          elevation: 5,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        ),
      ),
      child: Scaffold(
        appBar: AppBar(
          title: Text(
            'Admin Console - ${widget.teacherName}',
            style: const TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1.2),
          ),
          elevation: 0,
          backgroundColor: Colors.transparent,
          bottom: TabBar(
            controller: _tabController,
            indicatorColor: accentColor,
            indicatorWeight: 4,
            indicatorSize: TabBarIndicatorSize.label,
            labelColor: accentColor,
            unselectedLabelColor: Colors.white54,
            tabs: const [
              Tab(icon: Icon(Icons.analytics_outlined), text: 'Pulse'),
              Tab(icon: Icon(Icons.groups_outlined), text: 'Students'),
              Tab(icon: Icon(Icons.account_tree_outlined), text: 'Branches'),
              Tab(icon: Icon(Icons.history_outlined), text: 'Activity'),
            ],
          ),
          actions: [
            Padding(
              padding: const EdgeInsets.only(right: 8.0),
              child: IconButton(
                icon: const Icon(Icons.logout_rounded, color: Colors.redAccent),
                onPressed: () => Navigator.pop(context),
                tooltip: 'Logout',
              ),
            ),
          ],
        ),
        body: TabBarView(
          controller: _tabController,
          children: const [
            OverviewTab(),
            StudentsTab(),
            BranchTab(),
            ActivityTab(),
          ],
        ),
      ),
    );
  }
}

// ----------------------------------------------------------------------------
// Overview Tab
// ----------------------------------------------------------------------------
class OverviewTab extends StatefulWidget {
  const OverviewTab({Key? key}) : super(key: key);

  @override
  _OverviewTabState createState() => _OverviewTabState();
}

class _OverviewTabState extends State<OverviewTab> {
  Map<String, dynamic>? _overviewData;
  Map<String, dynamic>? _trendsData;
  String? _aiRecommendation;
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadAllData();
  }

  Future<void> _loadAllData() async {
    if (!mounted) return;
    setState(() { _isLoading = true; _error = null; });

    try {
      final results = await Future.wait([
        TeacherApiService.getDashboardOverview(),
        TeacherApiService.getBatchTrends(),
        TeacherApiService.getAiRecommendations(),
      ]);

      if (mounted) {
        setState(() {
          _overviewData = results[0];
          _trendsData = results[1];
          _aiRecommendation = results[2]['recommendation'];
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() { _error = e.toString(); _isLoading = false; });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) return const Center(child: CircularProgressIndicator(color: Color(0xFF24D876)));

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.wifi_off_rounded, size: 64, color: Colors.white24),
            const SizedBox(height: 16),
            Text('Connect Error: $_error', style: const TextStyle(color: Colors.white54)),
            const SizedBox(height: 20),
            ElevatedButton.icon(
              onPressed: _loadAllData,
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('Try Again'),
              style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF24D876), foregroundColor: Colors.black),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadAllData,
      color: const Color(0xFF24D876),
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          _buildAIInsightCard(),
          const SizedBox(height: 25),
          _buildQuickStats(),
          const SizedBox(height: 25),
          _buildSectionHeader("Performance Trends"),
          const SizedBox(height: 15),
          _buildTrendChart(),
          const SizedBox(height: 25),
          _buildSectionHeader("Branch Pulse"),
          const SizedBox(height: 15),
          _buildBranchDistribution(),
        ],
      ),
    );
  }

  Widget _buildAIInsightCard() {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [const Color(0xFF24D876).withOpacity(0.15), const Color(0xFF1D1E33)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: const Color(0xFF24D876).withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.auto_awesome_rounded, color: Color(0xFF24D876), size: 28),
              const SizedBox(width: 12),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: const [
                  Text("AI BATCH INSIGHTS", style: TextStyle(fontWeight: FontWeight.bold, letterSpacing: 2.0, color: Color(0xFF24D876), fontSize: 12)),
                  Text("Smart Recommendations", style: TextStyle(color: Colors.white38, fontSize: 10)),
                ],
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            _aiRecommendation ?? "Synthesizing batch performance data for you...",
            style: const TextStyle(fontSize: 15, height: 1.6, color: Colors.white70),
          ),
        ],
      ),
    );
  }

  Widget _buildQuickStats() {
    return Row(
      children: [
        Expanded(
          child: _buildGlassCard(
            "ENROLLED",
            _overviewData!['total_students'].toString(),
            Icons.school_outlined,
            Colors.blueAccent,
          ),
        ),
        const SizedBox(width: 15),
        Expanded(
          child: _buildGlassCard(
            "AT-RISK",
            _overviewData!['at_risk_count'].toString(),
            Icons.crisis_alert_rounded,
            Colors.redAccent,
          ),
        ),
      ],
    );
  }

  Widget _buildGlassCard(String title, String value, IconData icon, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 16),
      decoration: BoxDecoration(
        color: const Color(0xFF1D1E33),
        borderRadius: BorderRadius.circular(24),
      ),
      child: Column(
        children: [
          Icon(icon, color: color, size: 32),
          const SizedBox(height: 14),
          Text(value, style: const TextStyle(fontSize: 34, fontWeight: FontWeight.bold)),
          const SizedBox(height: 6),
          Text(title, style: const TextStyle(fontSize: 10, color: Colors.white30, fontWeight: FontWeight.bold, letterSpacing: 1.1)),
        ],
      ),
    );
  }

  Widget _buildTrendChart() {
    final trends = _trendsData?['trends'] as List? ?? [];
    if (trends.isEmpty) return const SizedBox(height: 100, child: Center(child: Text("No trend data available")));

    return Container(
      height: 250,
      padding: const EdgeInsets.fromLTRB(10, 20, 25, 10),
      decoration: BoxDecoration(color: const Color(0xFF1D1E33), borderRadius: BorderRadius.circular(24)),
      child: LineChart(
        LineChartData(
          gridData: FlGridData(show: true, drawVerticalLine: false, horizontalInterval: 2, getDrawingHorizontalLine: (v) => FlLine(color: Colors.white10, strokeWidth: 1)),
          titlesData: FlTitlesData(
            rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                getTitlesWidget: (val, meta) {
                  int idx = val.toInt();
                  if (idx >= 0 && idx < trends.length) return Padding(padding: const EdgeInsets.only(top: 8.0), child: Text(trends[idx]['week'], style: const TextStyle(fontSize: 10, color: Colors.white38)));
                  return const Text('');
                },
              ),
            ),
            leftTitles: AxisTitles(sideTitles: SideTitles(showTitles: true, reservedSize: 30, getTitlesWidget: (v, m) => Text("${(v*10).toInt()}%", style: const TextStyle(fontSize: 9, color: Colors.white24)))),
          ),
          borderData: FlBorderData(show: false),
          lineBarsData: [
            LineChartBarData(
              spots: List.generate(trends.length, (i) => FlSpot(i.toDouble(), (trends[i]['avg_score'] as num).toDouble() / 10)),
              isCurved: true,
              color: const Color(0xFF24D876),
              barWidth: 5,
              dotData: const FlDotData(show: true),
              belowBarData: BarAreaData(show: true, color: const Color(0xFF24D876).withOpacity(0.1)),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBranchDistribution() {
    final dist = _overviewData!['branch_distribution'] as Map<String, dynamic>;
    return Container(
      height: 280,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(color: const Color(0xFF1D1E33), borderRadius: BorderRadius.circular(24)),
      child: PieChart(
        PieChartData(
          sectionsSpace: 6,
          centerSpaceRadius: 50,
          sections: dist.entries.map((e) {
            return PieChartSectionData(
              color: Colors.primaries[dist.keys.toList().indexOf(e.key) % Colors.primaries.length],
              value: (e.value as num).toDouble(),
              title: e.key,
              radius: 60,
              titleStyle: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.white),
            );
          }).toList(),
        ),
      ),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Row(
      children: [
        Container(width: 5, height: 22, color: const Color(0xFF24D876)),
        const SizedBox(width: 12),
        Text(title.toUpperCase(), style: const TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1.5, color: Colors.white70, fontSize: 14)),
      ],
    );
  }
}

// ----------------------------------------------------------------------------
// Students Tab
// ----------------------------------------------------------------------------
class StudentsTab extends StatefulWidget {
  const StudentsTab({Key? key}) : super(key: key);

  @override
  _StudentsTabState createState() => _StudentsTabState();
}

class _StudentsTabState extends State<StudentsTab> {
  List<dynamic> _students = [];
  bool _isLoading = true;
  String? _error;
  String? _selectedBranch = 'All';
  final List<String> _branches = ['All', 'CSE', 'ECE', 'MECH', 'IT', 'CSBS', 'AEI'];

  @override
  void initState() {
    super.initState();
    _loadStudents();
  }

  Future<void> _loadStudents() async {
    if (!mounted) return;
    setState(() { _isLoading = true; _error = null; });
    try {
      final data = await TeacherApiService.getStudents(branch: _selectedBranch == 'All' ? null : _selectedBranch);
      if (mounted) {
        setState(() { _students = data['students']; _isLoading = false; });
      }
    } catch (e) {
      if (mounted) {
        setState(() { _error = e.toString(); _isLoading = false; });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 15),
          child: Row(
            children: _branches.map((b) => Padding(
              padding: const EdgeInsets.only(right: 12),
              child: ChoiceChip(
                label: Text(b),
                selected: _selectedBranch == b,
                onSelected: (s) { if(s) { setState(() => _selectedBranch = b); _loadStudents(); } },
                selectedColor: const Color(0xFF24D876),
                labelStyle: TextStyle(color: _selectedBranch == b ? Colors.black : Colors.white, fontWeight: FontWeight.bold),
                backgroundColor: const Color(0xFF1D1E33),
              ),
            )).toList(),
          ),
        ),
        Expanded(
          child: _isLoading 
            ? const Center(child: CircularProgressIndicator(color: Color(0xFF24D876)))
            : ListView.builder(
                padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
                itemCount: _students.length,
                itemBuilder: (context, idx) {
                  final s = _students[idx];
                  final double score = (s['avg_score'] as num).toDouble();
                  final bool isAtRisk = score < 40;
                  
                  return Card(
                    margin: const EdgeInsets.only(bottom: 16),
                    child: InkWell(
                      borderRadius: BorderRadius.circular(20),
                      onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => StudentDetailScreen(username: s['username']))),
                      child: Padding(
                        padding: const EdgeInsets.all(18),
                        child: Row(
                          children: [
                            Container(
                              width: 55,
                              height: 55,
                              decoration: BoxDecoration(
                                color: isAtRisk ? Colors.redAccent.withOpacity(0.1) : const Color(0xFF24D876).withOpacity(0.1),
                                shape: BoxShape.circle,
                              ),
                              child: Center(
                                child: Text(
                                  (s['username'] != null && s['username'].toString().isNotEmpty)
                                      ? s['username'].toString()[0].toUpperCase()
                                      : '?',
                                  style: TextStyle(color: isAtRisk ? Colors.redAccent : const Color(0xFF24D876), fontSize: 20, fontWeight: FontWeight.bold),
                                ),
                              ),
                            ),
                            const SizedBox(width: 18),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(s['username'], style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                                  const SizedBox(height: 4),
                                  Text("${s['branch']} • Level ${s['technical_level']}", style: const TextStyle(color: Colors.white38, fontSize: 12)),
                                  const SizedBox(height: 12),
                                  ClipRRect(
                                    borderRadius: BorderRadius.circular(10),
                                    child: LinearProgressIndicator(
                                      value: score / 100,
                                      minHeight: 6,
                                      backgroundColor: Colors.white10,
                                      color: isAtRisk ? Colors.redAccent : const Color(0xFF24D876),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(width: 18),
                            Column(
                              children: [
                                Text("${score.toInt()}%", style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: isAtRisk ? Colors.redAccent : const Color(0xFF24D876))),
                                const Text("SCORE", style: TextStyle(fontSize: 9, color: Colors.white24, fontWeight: FontWeight.bold)),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ),
                  );
                },
              ),
        ),
      ],
    );
  }
}

// ----------------------------------------------------------------------------
// Branch Tab
// ----------------------------------------------------------------------------
class BranchTab extends StatefulWidget {
  const BranchTab({Key? key}) : super(key: key);

  @override
  _BranchTabState createState() => _BranchTabState();
}

class _BranchTabState extends State<BranchTab> {
  String _selectedBranch = 'CSE';
  Map<String, dynamic>? _data;
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadBranchData();
  }

  Future<void> _loadBranchData() async {
    setState(() { _isLoading = true; _error = null; });
    try {
      final data = await TeacherApiService.getBranchAnalytics(_selectedBranch);
      setState(() { _data = data; _isLoading = false; });
    } catch (e) {
      setState(() { _error = e.toString(); _isLoading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 15),
          child: Row(
            children: [
              const Text("Branch:", style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white54)),
              const SizedBox(width: 15),
              Expanded(
                child: DropdownButtonHideUnderline(
                  child: DropdownButton<String>(
                    value: _selectedBranch,
                    dropdownColor: const Color(0xFF1D1E33),
                    items: ['CSE', 'ECE', 'MECH', 'IT', 'CSBS', 'AEI'].map((String b) {
                      return DropdownMenuItem<String>(value: b, child: Text(b, style: const TextStyle(fontWeight: FontWeight.bold)));
                    }).toList(),
                    onChanged: (String? val) { if(val != null) { setState(() => _selectedBranch = val); _loadBranchData(); } },
                  ),
                ),
              ),
            ],
          ),
        ),
        Expanded(
          child: _isLoading 
            ? const Center(child: CircularProgressIndicator(color: Color(0xFF24D876)))
            : ListView(
                padding: const EdgeInsets.all(20),
                children: [
                  _buildSummaryTile(),
                  const SizedBox(height: 25),
                  _buildSectionLabel("Category Strength"),
                  const SizedBox(height: 15),
                  _buildBarChart(),
                  const SizedBox(height: 25),
                  _buildSectionLabel("Top Performers"),
                  const SizedBox(height: 10),
                  ...((_data?['top_performers'] as List?) ?? []).map((p) => _buildPerformerCard(p)).toList(),
                ],
              ),
        ),
      ],
    );
  }

  Widget _buildSummaryTile() {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(color: const Color(0xFF1D1E33), borderRadius: BorderRadius.circular(24)),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          _buildMiniStat("TOTAL", _data!['total_students'].toString(), Icons.groups_3_outlined),
          _buildMiniStat("AVG SCORE", "${(_data!['category_averages'] as Map).values.fold(0.0, (p, c) => (p as double) + (c as num).toDouble()) / (_data!['category_averages'] as Map).length}%", Icons.insights_rounded),
        ],
      ),
    );
  }

  Widget _buildMiniStat(String label, String val, IconData icon) {
    return Column(
      children: [
        Icon(icon, color: const Color(0xFF24D876), size: 24),
        const SizedBox(height: 8),
        Text(val, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
        const SizedBox(height: 4),
        Text(label, style: const TextStyle(fontSize: 9, color: Colors.white24, fontWeight: FontWeight.bold)),
      ],
    );
  }

  Widget _buildBarChart() {
    final avgs = _data!['category_averages'] as Map<String, dynamic>;
    final categories = avgs.keys.toList();
    
    return Container(
      height: 200,
      padding: const EdgeInsets.fromLTRB(10, 20, 10, 10),
      decoration: BoxDecoration(color: const Color(0xFF1D1E33), borderRadius: BorderRadius.circular(24)),
      child: BarChart(
        BarChartData(
          titlesData: FlTitlesData(
            rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                getTitlesWidget: (v, m) {
                  int i = v.toInt();
                  if (i >= 0 && i < categories.length) return Padding(padding: const EdgeInsets.only(top: 8), child: Text(categories[i].toUpperCase(), style: const TextStyle(fontSize: 8, color: Colors.white38)));
                  return const Text('');
                },
              ),
            ),
          ),
          borderData: FlBorderData(show: false),
          barGroups: List.generate(categories.length, (i) => BarChartGroupData(x: i, barRods: [BarChartRodData(toY: (avgs[categories[i]] as num).toDouble(), color: const Color(0xFF24D876), width: 18, borderRadius: BorderRadius.circular(4))])),
        ),
      ),
    );
  }

  Widget _buildPerformerCard(dynamic p) {
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: ListTile(
        leading: const Icon(Icons.stars_rounded, color: Colors.amber),
        title: Text(p['username'], style: const TextStyle(fontWeight: FontWeight.bold)),
        trailing: Text("${p['avg_score']}%", style: const TextStyle(color: Color(0xFF24D876), fontWeight: FontWeight.bold)),
      ),
    );
  }

  Widget _buildSectionLabel(String text) => Text(text.toUpperCase(), style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, letterSpacing: 1.2, color: Colors.white54));
}

// ----------------------------------------------------------------------------
// Activity Tab
// ----------------------------------------------------------------------------
class ActivityTab extends StatefulWidget {
  const ActivityTab({Key? key}) : super(key: key);

  @override
  _ActivityTabState createState() => _ActivityTabState();
}

class _ActivityTabState extends State<ActivityTab> {
  Map<String, dynamic>? _data;
  bool _isLoading = true;
  String? _error;
  DateTime _selectedDate = DateTime.now();

  @override
  void initState() {
    super.initState();
    _loadActivity();
  }

  Future<void> _loadActivity() async {
    setState(() { _isLoading = true; _error = null; });
    try {
      final ds = '${_selectedDate.year}-${_selectedDate.month.toString().padLeft(2, '0')}-${_selectedDate.day.toString().padLeft(2, '0')}';
      final data = await TeacherApiService.getDailyActivity(date: ds);
      setState(() { _data = data; _isLoading = false; });
    } catch (e) {
      setState(() { _error = e.toString(); _isLoading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        _buildDatePicker(),
        const SizedBox(height: 25),
        if (_isLoading) const Center(child: CircularProgressIndicator(color: Color(0xFF24D876)))
        else if (_error != null) Center(child: Text("Error: $_error"))
        else ...[
          _buildActivityPulse(),
          const SizedBox(height: 25),
          _buildCompletionSummary(),
        ],
      ],
    );
  }

  Widget _buildDatePicker() {
    return InkWell(
      onTap: () async {
        final d = await showDatePicker(context: context, initialDate: _selectedDate, firstDate: DateTime(2024), lastDate: DateTime.now());
        if (d != null) { setState(() => _selectedDate = d); _loadActivity(); }
      },
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(color: const Color(0xFF1D1E33), borderRadius: BorderRadius.circular(20)),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Column(crossAxisAlignment: CrossAxisAlignment.start, children: const [Text("REPORT DATE", style: TextStyle(fontSize: 9, color: Colors.white30, fontWeight: FontWeight.bold)), SizedBox(height: 4), Text("Activity Log", style: TextStyle(fontWeight: FontWeight.bold))]),
            Text("${_selectedDate.day}/${_selectedDate.month}/${_selectedDate.year}", style: const TextStyle(color: Color(0xFF24D876), fontWeight: FontWeight.bold, fontSize: 18)),
          ],
        ),
      ),
    );
  }

  Widget _buildActivityPulse() {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(color: const Color(0xFF1D1E33), borderRadius: BorderRadius.circular(24)),
      child: Column(
        children: [
          Text("${_data?['completion_rate'] ?? 0}%", style: const TextStyle(fontSize: 48, fontWeight: FontWeight.bold, color: Color(0xFF24D876))),
          const Text("TOTAL COMPLETION", style: TextStyle(fontSize: 10, color: Colors.white24, fontWeight: FontWeight.bold)),
          const SizedBox(height: 25),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _buildSimpleStat("${_data?['students_completed'] ?? 0}", "SUCCESS", Colors.green),
              _buildSimpleStat("${_data?['students_missed'] ?? 0}", "MISSED", Colors.redAccent),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSimpleStat(String val, String label, Color color) => Column(children: [Text(val, style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: color)), Text(label, style: const TextStyle(fontSize: 9, color: Colors.white24))]);

  Widget _buildCompletionSummary() {
    final details = (_data?['completed_details'] as List?) ?? [];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text("COMPLETED BY", style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white54)),
        const SizedBox(height: 10),
        if (details.isEmpty) const Text("No completions recorded for this day.", style: TextStyle(color: Colors.white24))
        else ...details.map((d) => Card(child: ListTile(title: Text(d['username']), subtitle: Text(d['branch']), trailing: const Icon(Icons.check_circle, color: Color(0xFF24D876))))),
      ],
    );
  }
}
