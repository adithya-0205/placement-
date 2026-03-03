import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import 'login_screen.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _userController = TextEditingController();
  final _passController = TextEditingController();
  String _selectedRole = "Student"; 
  String? _selectedBranch; // Added for branch selection

  @override
  Widget build(BuildContext context) {
    // Consistent theme colors from your figure
    const Color scaffoldBg = Color(0xFF0F0C29);
    const Color accentColor = Color(0xFF6C63FF);

    return Scaffold(
      backgroundColor: scaffoldBg,
      body: Row(
        children: [
          // --- LEFT SIDE: Brand & Registration Info ---
          Expanded(
            flex: 1,
            child: Container(
              padding: const EdgeInsets.all(40),
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [Color(0xFF1A237E), Color(0xFF4A148C)],
                ),
              ),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.person_add_outlined, size: 60, color: Colors.white),
                  const SizedBox(height: 20),
                  const Text(
                    "Join the Future of Placement",
                    style: TextStyle(fontSize: 42, fontWeight: FontWeight.bold, color: Colors.white),
                  ),
                  const Text(
                    "Create an account to access AI-powered mock interviews and personalized analytics.",
                    style: TextStyle(fontSize: 18, color: Colors.white70),
                  ),
                  const SizedBox(height: 40),
                  _buildFeatureRow(Icons.verified_user_outlined, "Secure Profile", "Your data is encrypted and used only for your growth."),
                  _buildFeatureRow(Icons.auto_graph, "Personalized Roadmap", "Get custom preparation paths based on your performance."),
                  _buildFeatureRow(Icons.bolt, "Instant Access", "Start practicing immediately after signing up."),
                ],
              ),
            ),
          ),

          // --- RIGHT SIDE: Registration Form ---
          Expanded(
            flex: 1,
            child: Center(
              child: Container(
                constraints: const BoxConstraints(maxWidth: 450),
                child: ListView(
                  shrinkWrap: true, // Key to keep it centered if possible
                  padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 40),
                  children: [
                    const Text("Create Account", style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: Colors.white)),
                    const Text("Fill in the details to get started", style: TextStyle(color: Colors.white54)),
                    const SizedBox(height: 30),
  
                    // Role Selection (Matches Login Screen)
                    const Text("I am a:", style: TextStyle(color: Colors.white70, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        _roleButton("Student", Icons.person_outline, _selectedRole == "Student"),
                        const SizedBox(width: 15),
                        _roleButton("Teacher", Icons.groups_outlined, _selectedRole == "Teacher"),
                      ],
                    ),
                    const SizedBox(height: 25),
  
                    // Input Fields (Glassmorphic Style)
                    _buildTextField("Username / Email", _userController, Icons.account_circle_outlined),
                    const SizedBox(height: 20),
                    _buildTextField("Create Password", _passController, Icons.lock_reset_outlined, isPassword: true),
                    const SizedBox(height: 20),
  
                    // Branch Selection (Only if Student)
                    if (_selectedRole == "Student") ...[
                      const Text("Select Branch:", style: TextStyle(color: Colors.white70, fontSize: 14)),
                      const SizedBox(height: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12),
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.05),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: DropdownButtonHideUnderline(
                          child: DropdownButton<String>(
                            value: _selectedBranch,
                            hint: const Text("Choose Branch", style: TextStyle(color: Colors.white38)),
                            isExpanded: true,
                            dropdownColor: const Color(0xFF161625),
                            icon: const Icon(Icons.arrow_drop_down, color: Colors.white54),
                            style: const TextStyle(color: Colors.white),
                            items: ["CSE", "IT", "AI&DS", "CSBS", "ECE", "EEE", "AEI", "MECH", "CIVIL"].map((String branch) {
                              return DropdownMenuItem<String>(
                                value: branch,
                                child: Text(branch),
                              );
                            }).toList(),
                            onChanged: (val) => setState(() => _selectedBranch = val),
                          ),
                        ),
                      ),
                      const SizedBox(height: 20),
                    ],
  
                    // Original Registration Logic
                    ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: accentColor,
                        minimumSize: const Size(double.infinity, 55),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      onPressed: () async {
                        if (_userController.text.isEmpty || _passController.text.isEmpty) {
                           ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Please fill all fields")));
                           return;
                        }

                        if (_selectedRole == "Student" && _selectedBranch == null) {
                           ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Please select a branch")));
                           return;
                        }

                        final success = await Provider.of<AuthProvider>(context, listen: false)
                            .register(_userController.text, _passController.text, _selectedBranch, _selectedRole.toLowerCase());
  
                        if (success && context.mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text("Registration Successful! Please Login.")),
                          );
                          Navigator.pop(context); // Go back to Login
                        } else {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text("Registration Failed")),
                          );
                        }
                      },
                      child: const Text("Create Account", style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                    ),
  
                    const SizedBox(height: 20),
                    Center(
                      child: TextButton(
                        onPressed: () => Navigator.pop(context),
                        child: const Text("Already have an account? Login here", style: TextStyle(color: Colors.white70)),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  // --- UI HELPER COMPONENTS ---

  Widget _roleButton(String title, IconData icon, bool isSelected) {
    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() => _selectedRole = title),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 15),
          decoration: BoxDecoration(
            color: isSelected ? const Color(0xFF6C63FF).withOpacity(0.2) : Colors.white.withOpacity(0.05),
            border: Border.all(color: isSelected ? const Color(0xFF6C63FF) : Colors.white12, width: 2),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Column(
            children: [
              Icon(icon, color: isSelected ? Colors.white : Colors.white54),
              const SizedBox(height: 5),
              Text(title, style: TextStyle(color: isSelected ? Colors.white : Colors.white54)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTextField(String label, TextEditingController controller, IconData icon, {bool isPassword = false}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(color: Colors.white70, fontSize: 14)),
        const SizedBox(height: 8),
        TextField(
          controller: controller,
          obscureText: isPassword,
          style: const TextStyle(color: Colors.white),
          decoration: InputDecoration(
            prefixIcon: Icon(icon, color: Colors.white38),
            filled: true,
            fillColor: Colors.white.withOpacity(0.05),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
            hintText: label,
            hintStyle: const TextStyle(color: Colors.white24, fontSize: 14),
          ),
        ),
      ],
    );
  }

  Widget _buildFeatureRow(IconData icon, String title, String subtitle) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 25.0),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(color: Colors.white10, borderRadius: BorderRadius.circular(10)),
            child: Icon(icon, color: Colors.white, size: 24),
          ),
          const SizedBox(width: 20),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)),
                Text(subtitle, style: const TextStyle(color: Colors.white54, fontSize: 13), softWrap: true),
              ],
            ),
          )
        ],
      ),
    );
  }
}