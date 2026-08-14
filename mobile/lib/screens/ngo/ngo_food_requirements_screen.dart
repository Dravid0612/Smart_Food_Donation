import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../providers/ngo_provider.dart';
import '../../widgets/custom_card.dart';
import '../../widgets/loading_indicator.dart';

class NgoFoodRequirementsScreen extends StatefulWidget {
  const NgoFoodRequirementsScreen({super.key});

  @override
  State<NgoFoodRequirementsScreen> createState() => _NgoFoodRequirementsScreenState();
}

class _NgoFoodRequirementsScreenState extends State<NgoFoodRequirementsScreen> {
  // Each food type maps to a required quantity
  final Map<String, int> _requirements = {
    'Cooked Rice Meals': 100,
    'Bread & Bakery': 50,
    'Packaged Food': 80,
    'Fruits': 30,
    'Vegetables': 40,
    'Cooked Non-Veg': 60,
  };

  // Simulated received amounts (would come from backend in production)
  final Map<String, int> _received = {
    'Cooked Rice Meals': 35,
    'Bread & Bakery': 20,
    'Packaged Food': 60,
    'Fruits': 10,
    'Vegetables': 15,
    'Cooked Non-Veg': 20,
  };

  bool _isSaving = false;

  Future<void> _saveRequirements() async {
    setState(() => _isSaving = true);
    // In production: call ngoProvider.updateFoodRequirements(_requirements)
    await Future.delayed(const Duration(seconds: 1));
    if (mounted) {
      setState(() => _isSaving = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Food requirements saved! Smart matching updated.'),
          backgroundColor: Color(0xFF10B981),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Food Requirements'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        actions: [
          TextButton(
            onPressed: _isSaving ? null : _saveRequirements,
            child: _isSaving
                ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                : const Text('Save', style: TextStyle(fontWeight: FontWeight.bold)),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFFECFDF5),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: const Color(0xFFA7F3D0)),
              ),
              child: const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.auto_awesome, color: Color(0xFF10B981), size: 20),
                      SizedBox(width: 8),
                      Text('Smart Matching Enabled',
                          style: TextStyle(fontWeight: FontWeight.bold, color: Color(0xFF065F46))),
                    ],
                  ),
                  SizedBox(height: 6),
                  Text(
                    'Set how much of each food type your NGO needs. The smart matching system will prioritize donations that meet your requirements.',
                    style: TextStyle(color: Color(0xFF047857), fontSize: 12),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            const Text('Required Quantities', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            const Text('Set how many meals/units you need for each category.',
                style: TextStyle(color: Color(0xFF64748B), fontSize: 13)),
            const SizedBox(height: 16),

            // Requirements list
            ..._requirements.entries.map((entry) {
              final foodType = entry.key;
              final required = entry.value;
              final received = _received[foodType] ?? 0;
              final progress = (received / required).clamp(0.0, 1.0);
              final isMet = received >= required;

              return CustomCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(foodType,
                              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                        ),
                        if (isMet)
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(
                              color: const Color(0xFFD1FAE5),
                              borderRadius: BorderRadius.circular(20),
                            ),
                            child: const Text('Need Met ✓',
                                style: TextStyle(color: Color(0xFF047857), fontSize: 11, fontWeight: FontWeight.bold)),
                          ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Text('Received: $received',
                                      style: const TextStyle(fontSize: 12, color: Color(0xFF64748B))),
                                  Text('Required: $required',
                                      style: const TextStyle(fontSize: 12, color: Color(0xFF64748B))),
                                ],
                              ),
                              const SizedBox(height: 6),
                              ClipRRect(
                                borderRadius: BorderRadius.circular(4),
                                child: LinearProgressIndicator(
                                  value: progress,
                                  backgroundColor: Colors.grey.shade200,
                                  valueColor: AlwaysStoppedAnimation<Color>(
                                    isMet ? const Color(0xFF10B981) : const Color(0xFFF59E0B),
                                  ),
                                  minHeight: 8,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 16),
                        SizedBox(
                          width: 80,
                          child: TextFormField(
                            initialValue: required.toString(),
                            keyboardType: TextInputType.number,
                            textAlign: TextAlign.center,
                            decoration: InputDecoration(
                              contentPadding: const EdgeInsets.symmetric(vertical: 8, horizontal: 8),
                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                              isDense: true,
                            ),
                            onChanged: (val) {
                              final n = int.tryParse(val);
                              if (n != null && n > 0) {
                                setState(() => _requirements[foodType] = n);
                              }
                            },
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              );
            }),
            const SizedBox(height: 24),

            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _isSaving ? null : _saveRequirements,
                child: _isSaving
                    ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                    : const Text('Save Requirements'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
