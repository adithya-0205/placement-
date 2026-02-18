import 'package:flutter/material.dart';
import '../services/teacher_api_service.dart';

class StudentDetailScreen extends StatefulWidget {
  final String username;

  const StudentDetailScreen({
    Key? key,
    required this.username,
  }) : super(key: key);

  @override
  _StudentDetailScreenState createState() => _StudentDetailScreenState();
}

class _StudentDetailScreenState extends State<StudentDetailScreen> {
  Map<String, dynamic>? _data;
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadStudentData();
  }

  Future<void> _loadStudentData() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final data = await TeacherApiService.getStudentProgress(widget.username);
      setState(() {
        _data = data;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Student: ${widget.username}'),
        backgroundColor: Colors.blue.shade700,
        foregroundColor: Colors.white,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.error_outline, size: 64, color: Colors.red.shade300),
                      const SizedBox(height: 16),
                      Text('Error: $_error'),
                      const SizedBox(height: 16),
                      ElevatedButton(
                        onPressed: _loadStudentData,
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _loadStudentData,
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      // Student Profile Card
                      Card(
                        color: Colors.blue.shade50,
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  CircleAvatar(
                                    radius: 30,
                                    backgroundColor: Colors.blue.shade700,
                                    child: Text(
                                      widget.username[0].toUpperCase(),
                                      style: const TextStyle(
                                        fontSize: 24,
                                        color: Colors.white,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                  ),
                                  const SizedBox(width: 16),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          _data!['student']['username'],
                                          style: const TextStyle(
                                            fontSize: 20,
                                            fontWeight: FontWeight.bold,
                                          ),
                                        ),
                                        Text('Branch: ${_data!['student']['branch']}'),
                                        Text(
                                          'Joined: ${_data!['student']['joined_date']}',
                                          style: TextStyle(
                                            fontSize: 12,
                                            color: Colors.grey.shade600,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                              const Divider(height: 24),
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceAround,
                                children: [
                                  _buildStatChip(
                                    'Aptitude Level',
                                    _data!['student']['aptitude_level'].toString(),
                                    Colors.purple,
                                  ),
                                  _buildStatChip(
                                    'Technical Level',
                                    _data!['student']['technical_level'].toString(),
                                    Colors.orange,
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),

                      // Completion Streak
                      Card(
                        child: ListTile(
                          leading: const Icon(Icons.local_fire_department, color: Colors.orange),
                          title: const Text('7-Day Completion Streak'),
                          trailing: Text(
                            '${_data!['completion_last_7_days']} days',
                            style: const TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                              color: Colors.orange,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),

                      // Category Stats
                      if ((_data!['category_stats'] as Map).isNotEmpty)
                        Card(
                          child: Padding(
                            padding: const EdgeInsets.all(16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text(
                                  'Performance by Category',
                                  style: TextStyle(
                                    fontSize: 18,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                const SizedBox(height: 16),
                                ...(_data!['category_stats'] as Map<String, dynamic>)
                                    .entries
                                    .map((entry) => Padding(
                                          padding: const EdgeInsets.symmetric(vertical: 8),
                                          child: Column(
                                            crossAxisAlignment: CrossAxisAlignment.start,
                                            children: [
                                              Text(
                                                entry.key.toUpperCase(),
                                                style: const TextStyle(
                                                  fontWeight: FontWeight.bold,
                                                ),
                                              ),
                                              const SizedBox(height: 4),
                                              Row(
                                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                                children: [
                                                  Text('Quizzes: ${entry.value['total_quizzes']}'),
                                                  Text('Avg: ${entry.value['avg_score']}%'),
                                                  Text('Best: ${entry.value['best_score']}%'),
                                                ],
                                              ),
                                            ],
                                          ),
                                        ))
                                    .toList(),
                              ],
                            ),
                          ),
                        ),
                      const SizedBox(height: 16),

                      // Weak Areas
                      if ((_data!['weak_areas'] as List).isNotEmpty)
                        Card(
                          color: Colors.orange.shade50,
                          child: Padding(
                            padding: const EdgeInsets.all(16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Icon(Icons.warning, color: Colors.orange.shade700),
                                    const SizedBox(width: 8),
                                    const Text(
                                      'Weak Areas (Need Improvement)',
                                      style: TextStyle(
                                        fontSize: 18,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 16),
                                ...(_data!['weak_areas'] as List).map((area) => ListTile(
                                      leading: const Icon(Icons.trending_down, color: Colors.red),
                                      title: Text(area['area']),
                                      subtitle: Text('${area['attempts']} attempts'),
                                      trailing: Text(
                                        '${area['avg_score']}%',
                                        style: const TextStyle(
                                          fontWeight: FontWeight.bold,
                                          color: Colors.red,
                                        ),
                                      ),
                                    )),
                              ],
                            ),
                          ),
                        ),
                      const SizedBox(height: 16),

                      // Quiz History
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text(
                                'Recent Quiz History',
                                style: TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              const SizedBox(height: 16),
                              if ((_data!['quiz_history'] as List).isEmpty)
                                const Text('No quiz history available')
                              else
                                ...(_data!['quiz_history'] as List).take(10).map((quiz) => Card(
                                      margin: const EdgeInsets.symmetric(vertical: 4),
                                      child: ListTile(
                                        leading: CircleAvatar(
                                          backgroundColor: quiz['percentage'] >= 70
                                              ? Colors.green
                                              : quiz['percentage'] >= 50
                                                  ? Colors.orange
                                                  : Colors.red,
                                          child: Text(
                                            '${quiz['percentage']}%',
                                            style: const TextStyle(
                                              color: Colors.white,
                                              fontSize: 12,
                                              fontWeight: FontWeight.bold,
                                            ),
                                          ),
                                        ),
                                        title: Text(quiz['category'].toUpperCase()),
                                        subtitle: Text(
                                          '${quiz['area']} - ${quiz['date']}',
                                          style: const TextStyle(fontSize: 12),
                                        ),
                                        trailing: Text(
                                          '${quiz['score']}/${quiz['total']}',
                                          style: const TextStyle(fontWeight: FontWeight.bold),
                                        ),
                                      ),
                                    )),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
    );
  }

  Widget _buildStatChip(String label, String value, Color color) {
    return Column(
      children: [
        Text(
          value,
          style: TextStyle(
            fontSize: 24,
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey.shade600,
          ),
        ),
      ],
    );
  }
}
