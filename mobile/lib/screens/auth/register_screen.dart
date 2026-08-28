import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/auth_provider.dart';

class RegisterScreen extends StatefulWidget {
  final String? initialRole;
  const RegisterScreen({super.key, this.initialRole});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();
  final _phoneController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  final _addressController = TextEditingController();
  final _orgNameController = TextEditingController();
  final _capacityController = TextEditingController(text: '100');

  String _selectedRole = 'donor'; // donor, ngo, volunteer
  String _selectedVehicleType = 'bike'; // walking, bike, car, van
  int _selectedCarryingCapacity = 50; // 10, 50, 150, 500

  @override
  void initState() {
    super.initState();
    if (widget.initialRole != null &&
        ['donor', 'ngo', 'volunteer'].contains(widget.initialRole!.toLowerCase())) {
      _selectedRole = widget.initialRole!.toLowerCase();
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _phoneController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    _addressController.dispose();
    _orgNameController.dispose();
    _capacityController.dispose();
    super.dispose();
  }

  Future<void> _handleRegister() async {
    if (!_formKey.currentState!.validate()) return;

    if (_passwordController.text != _confirmPasswordController.text) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(context.tr('password_mismatch')), backgroundColor: AppTheme.error),
      );
      return;
    }

    final authProvider = Provider.of<AuthProvider>(context, listen: false);
    final success = await authProvider.register(
      name: _nameController.text.trim(),
      email: _emailController.text.trim(),
      password: _passwordController.text,
      phone: _phoneController.text.trim(),
      role: _selectedRole,
      address: _addressController.text.trim(),
      organizationName: _selectedRole == 'ngo' ? _orgNameController.text.trim() : null,
      capacity: _selectedRole == 'ngo' ? int.tryParse(_capacityController.text) ?? 100 : null,
      vehicleType: _selectedRole == 'volunteer' ? _selectedVehicleType : null,
      carryingCapacity: _selectedRole == 'volunteer' ? _selectedCarryingCapacity : null,
    );

    if (!mounted) return;

    if (success) {
      final role = authProvider.currentUser?.role ?? 'donor';
      switch (role.toLowerCase()) {
        case 'donor':
          context.go('/donor');
          break;
        case 'ngo':
          context.go('/ngo');
          break;
        case 'volunteer':
          context.go('/volunteer');
          break;
        default:
          context.go('/donor');
      }
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(context.trError(authProvider.errorMessage ?? 'Registration failed')),
          backgroundColor: AppTheme.error,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final authProvider = Provider.of<AuthProvider>(context);

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        title: Text(context.tr('register')),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/login'),
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  context.tr('join_mission'),
                  style: const TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF1E293B),
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  context.tr('select_role'),
                  style: const TextStyle(color: Color(0xFF64748B), fontSize: 13),
                ),
                const SizedBox(height: 16),

                // Role Selector Segmented Buttons
                SegmentedButton<String>(
                  segments: [
                    ButtonSegment(value: 'donor', label: Text(context.trRole('donor')), icon: const Icon(Icons.volunteer_activism)),
                    ButtonSegment(value: 'ngo', label: Text(context.trRole('ngo')), icon: const Icon(Icons.maps_home_work)),
                    ButtonSegment(value: 'volunteer', label: Text(context.trRole('volunteer')), icon: const Icon(Icons.directions_bike)),
                  ],
                  selected: {_selectedRole},
                  onSelectionChanged: (Set<String> newSelection) {
                    setState(() => _selectedRole = newSelection.first);
                  },
                ),
                const SizedBox(height: 20),

                // Notice for NGO
                if (_selectedRole == 'ngo') ...[
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.amber.shade50,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: Colors.amber.shade300),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.verified_user_outlined, color: Color(0xFFB45309), size: 20),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            context.tr('why_verify'),
                            style: const TextStyle(color: Color(0xFF92400E), fontSize: 12),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                ],

                // Name / Contact Name
                TextFormField(
                  controller: _nameController,
                  decoration: InputDecoration(
                    labelText: _selectedRole == 'donor'
                        ? '${context.tr('full_name')} / ${context.tr('role_donor')}'
                        : _selectedRole == 'ngo'
                            ? '${context.tr('full_name')} (NGO)'
                            : context.tr('full_name'),
                    prefixIcon: const Icon(Icons.person_outline),
                  ),
                  validator: (v) => v == null || v.trim().isEmpty ? context.tr('field_required') : null,
                ),
                const SizedBox(height: 16),

                // NGO Organization Name & Capacity
                if (_selectedRole == 'ngo') ...[
                  TextFormField(
                    controller: _orgNameController,
                    decoration: InputDecoration(
                      labelText: '${context.tr('role_ngo')} ${context.tr('full_name')}',
                      prefixIcon: const Icon(Icons.business),
                    ),
                    validator: (v) => v == null || v.trim().isEmpty ? context.tr('field_required') : null,
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: _capacityController,
                    keyboardType: TextInputType.number,
                    decoration: InputDecoration(
                      labelText: '${context.tr('payload_capacity')} (${context.tr('unit_meals')})',
                      prefixIcon: const Icon(Icons.storage),
                    ),
                    validator: (v) => v == null || v.trim().isEmpty ? context.tr('field_required') : null,
                  ),
                  const SizedBox(height: 16),
                ],

                // Volunteer Vehicle & Capacity Fields
                if (_selectedRole == 'volunteer') ...[
                  DropdownButtonFormField<String>(
                    initialValue: _selectedVehicleType,
                    decoration: InputDecoration(
                      labelText: context.tr('vehicle_type'),
                      prefixIcon: const Icon(Icons.directions_car),
                    ),
                    items: const [
                      DropdownMenuItem(value: 'walking', child: Text('Walking / On Foot')),
                      DropdownMenuItem(value: 'bike', child: Text('Two-Wheeler / Motorbike')),
                      DropdownMenuItem(value: 'car', child: Text('Four-Wheeler / Car')),
                      DropdownMenuItem(value: 'van', child: Text('Van / Mini-Truck')),
                    ],
                    onChanged: (val) {
                      if (val != null) {
                        setState(() {
                          _selectedVehicleType = val;
                          if (val == 'walking') {
                            _selectedCarryingCapacity = 10;
                          } else if (val == 'bike') {
                            _selectedCarryingCapacity = 50;
                          } else if (val == 'car') {
                            _selectedCarryingCapacity = 150;
                          } else if (val == 'van') {
                            _selectedCarryingCapacity = 500;
                          }
                        });
                      }
                    },
                  ),
                  const SizedBox(height: 16),
                  DropdownButtonFormField<int>(
                    initialValue: _selectedCarryingCapacity,
                    decoration: InputDecoration(
                      labelText: context.tr('payload_capacity'),
                      prefixIcon: const Icon(Icons.fitness_center),
                    ),
                    items: [
                      DropdownMenuItem(value: 10, child: Text('10 ${context.tr('unit_meals')} (Compact)')),
                      DropdownMenuItem(value: 50, child: Text('50 ${context.tr('unit_meals')} (Medium - Bike)')),
                      DropdownMenuItem(value: 150, child: Text('150 ${context.tr('unit_meals')} (Large - Car)')),
                      DropdownMenuItem(value: 500, child: Text('500 ${context.tr('unit_meals')} (Bulk - Van)')),
                    ],
                    onChanged: (val) {
                      if (val != null) {
                        setState(() => _selectedCarryingCapacity = val);
                      }
                    },
                  ),
                  const SizedBox(height: 16),
                ],

                // Email
                TextFormField(
                  controller: _emailController,
                  keyboardType: TextInputType.emailAddress,
                  decoration: InputDecoration(
                    labelText: context.tr('email'),
                    prefixIcon: const Icon(Icons.email_outlined),
                  ),
                  validator: (v) => v == null || !v.contains('@') ? context.tr('enter_email') : null,
                ),
                const SizedBox(height: 16),

                // Phone
                TextFormField(
                  controller: _phoneController,
                  keyboardType: TextInputType.phone,
                  decoration: InputDecoration(
                    labelText: context.tr('phone_number'),
                    prefixIcon: const Icon(Icons.phone_outlined),
                  ),
                  validator: (v) => v == null || v.trim().isEmpty ? context.tr('field_required') : null,
                ),
                const SizedBox(height: 16),

                // Address
                TextFormField(
                  controller: _addressController,
                  decoration: InputDecoration(
                    labelText: context.tr('pickup_address'),
                    prefixIcon: const Icon(Icons.location_on_outlined),
                  ),
                  validator: (v) => v == null || v.trim().isEmpty ? context.tr('field_required') : null,
                ),
                const SizedBox(height: 16),

                // Password
                TextFormField(
                  controller: _passwordController,
                  obscureText: true,
                  decoration: InputDecoration(
                    labelText: context.tr('password'),
                    prefixIcon: const Icon(Icons.lock_outline),
                  ),
                  validator: (v) => v == null || v.length < 6 ? context.tr('enter_password') : null,
                ),
                const SizedBox(height: 16),

                // Confirm Password
                TextFormField(
                  controller: _confirmPasswordController,
                  obscureText: true,
                  decoration: InputDecoration(
                    labelText: context.tr('confirm_password'),
                    prefixIcon: const Icon(Icons.lock_outline),
                  ),
                  validator: (v) => v == null || v.isEmpty ? context.tr('confirm_password') : null,
                ),
                const SizedBox(height: 24),

                // Register Button
                ElevatedButton(
                  onPressed: authProvider.isLoading ? null : _handleRegister,
                  child: authProvider.isLoading
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                        )
                      : Text(context.tr('register')),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
