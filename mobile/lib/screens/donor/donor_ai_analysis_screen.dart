import 'dart:io';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// AI Food Condition Analysis Screen.
/// Simulates an on-device analysis of the uploaded food image.
/// Clearly disclaims that image analysis cannot guarantee food safety.
class DonorAiAnalysisScreen extends StatefulWidget {
  final String? imagePath;
  const DonorAiAnalysisScreen({super.key, this.imagePath});

  @override
  State<DonorAiAnalysisScreen> createState() => _DonorAiAnalysisScreenState();
}

class _DonorAiAnalysisScreenState extends State<DonorAiAnalysisScreen>
    with TickerProviderStateMixin {
  bool _analyzing = true;
  late AnimationController _pulseController;
  late Map<String, dynamic> _results;

  // Simulated analysis steps
  final List<String> _analysisSteps = [
    'Initializing food detection...',
    'Scanning for visible spoilage...',
    'Analyzing packaging integrity...',
    'Checking discoloration patterns...',
    'Computing condition score...',
  ];
  int _currentStep = 0;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 1),
    )..repeat(reverse: true);

    _runAnalysis();
  }

  Future<void> _runAnalysis() async {
    for (int i = 0; i < _analysisSteps.length; i++) {
      await Future.delayed(const Duration(milliseconds: 700));
      if (mounted) setState(() => _currentStep = i);
    }
    await Future.delayed(const Duration(milliseconds: 500));
    if (mounted) {
      setState(() {
        _analyzing = false;
        _results = _generateSimulatedResults();
      });
    }
  }

  Map<String, dynamic> _generateSimulatedResults() {
    // Simulate a mostly-good result (realistic for a hackathon demo)
    final rng = Random();
    final score = 70 + rng.nextInt(25); // 70–94
    String condition;
    Color conditionColor;
    IconData conditionIcon;
    if (score >= 85) {
      condition = 'Good Visible Condition';
      conditionColor = const Color(0xFF10B981);
      conditionIcon = Icons.check_circle;
    } else if (score >= 70) {
      condition = 'Needs Attention';
      conditionColor = const Color(0xFFF59E0B);
      conditionIcon = Icons.warning_amber_rounded;
    } else {
      condition = 'Visible Spoilage Detected';
      conditionColor = const Color(0xFFEF4444);
      conditionIcon = Icons.cancel;
    }
    return {
      'score': score,
      'condition': condition,
      'conditionColor': conditionColor,
      'conditionIcon': conditionIcon,
      'foodDetection': 'Cooked/Prepared Food',
      'spoilage': score >= 85 ? 'None detected' : score >= 70 ? 'Minor signs' : 'Visible signs',
      'spoilageStatus': score >= 85 ? 'pass' : score >= 70 ? 'warn' : 'fail',
      'packaging': score >= 80 ? 'Intact packaging' : 'Some exposure detected',
      'packagingStatus': score >= 80 ? 'pass' : 'warn',
      'discoloration': score >= 85 ? 'Normal color range' : 'Slight variation detected',
      'discolorationStatus': score >= 85 ? 'pass' : 'warn',
    };
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0F172A),
        title: const Text('AI Food Analysis', style: TextStyle(color: Colors.white)),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.white),
          onPressed: () => context.pop(),
        ),
        iconTheme: const IconThemeData(color: Colors.white),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Image preview
            if (widget.imagePath != null)
              ClipRRect(
                borderRadius: BorderRadius.circular(20),
                child: Image.file(
                  File(widget.imagePath!),
                  height: 220,
                  width: double.infinity,
                  fit: BoxFit.cover,
                ),
              )
            else
              Container(
                height: 220,
                decoration: BoxDecoration(
                  color: const Color(0xFF1E293B),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: const Center(
                  child: Icon(Icons.fastfood, color: Colors.white38, size: 60),
                ),
              ),
            const SizedBox(height: 24),

            if (_analyzing) _buildAnalyzingView() else _buildResultsView(),
          ],
        ),
      ),
    );
  }

  Widget _buildAnalyzingView() {
    return Column(
      children: [
        AnimatedBuilder(
          animation: _pulseController,
          builder: (_, __) => Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Color.lerp(
                const Color(0xFF10B981).withOpacity(0.05),
                const Color(0xFF10B981).withOpacity(0.15),
                _pulseController.value,
              ),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: const Color(0xFF10B981).withOpacity(0.3)),
            ),
            child: Column(
              children: [
                const CircularProgressIndicator(color: Color(0xFF10B981)),
                const SizedBox(height: 16),
                const Text(
                  'Analyzing Food Image...',
                  style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 20),
                ...List.generate(_analysisSteps.length, (i) {
                  final done = i < _currentStep;
                  final active = i == _currentStep;
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 6),
                    child: Row(
                      children: [
                        Icon(
                          done ? Icons.check_circle : active ? Icons.radio_button_checked : Icons.radio_button_unchecked,
                          color: done ? const Color(0xFF10B981) : active ? Colors.white : Colors.white24,
                          size: 18,
                        ),
                        const SizedBox(width: 12),
                        Text(
                          _analysisSteps[i],
                          style: TextStyle(
                            color: done ? const Color(0xFF10B981) : active ? Colors.white : Colors.white24,
                            fontSize: 13,
                          ),
                        ),
                      ],
                    ),
                  );
                }),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildResultsView() {
    final r = _results;
    final conditionColor = r['conditionColor'] as Color;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Overall Condition Badge
        Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: conditionColor.withOpacity(0.12),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: conditionColor.withOpacity(0.4)),
          ),
          child: Column(
            children: [
              Icon(r['conditionIcon'] as IconData, color: conditionColor, size: 48),
              const SizedBox(height: 12),
              Text(
                r['condition'] as String,
                style: TextStyle(color: conditionColor, fontSize: 22, fontWeight: FontWeight.bold),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              Text(
                'Condition Score: ${r['score']}/100',
                style: const TextStyle(color: Colors.white60, fontSize: 14),
              ),
            ],
          ),
        ),
        const SizedBox(height: 20),

        // Detailed Breakdown
        const Text(
          'Analysis Breakdown',
          style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),
        _buildResultRow('🍱 Food Detection', r['foodDetection'] as String, 'pass'),
        _buildResultRow('🔴 Spoilage Detection', r['spoilage'] as String, r['spoilageStatus'] as String),
        _buildResultRow('📦 Packaging Analysis', r['packaging'] as String, r['packagingStatus'] as String),
        _buildResultRow('🎨 Discoloration', r['discoloration'] as String, r['discolorationStatus'] as String),
        const SizedBox(height: 20),

        // Disclaimer
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: Colors.amber.withOpacity(0.1),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: Colors.amber.withOpacity(0.3)),
          ),
          child: const Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(Icons.info_outline, color: Colors.amber, size: 18),
              SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Image analysis cannot guarantee food safety. This is a visual assessment only. Please use your own judgment before donating.',
                  style: TextStyle(color: Colors.amber, fontSize: 12),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 28),

        // Action Buttons
        ElevatedButton(
          onPressed: () => context.go('/donor/create'),
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF10B981),
            padding: const EdgeInsets.symmetric(vertical: 16),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          ),
          child: const Text('Continue Donation →', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white)),
        ),
        const SizedBox(height: 12),
        OutlinedButton(
          onPressed: () => context.pop(),
          style: OutlinedButton.styleFrom(
            foregroundColor: Colors.white54,
            side: const BorderSide(color: Colors.white24),
            padding: const EdgeInsets.symmetric(vertical: 14),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          ),
          child: const Text('Retake Photo'),
        ),
      ],
    );
  }

  Widget _buildResultRow(String label, String value, String status) {
    Color statusColor;
    IconData statusIcon;
    switch (status) {
      case 'pass':
        statusColor = const Color(0xFF10B981);
        statusIcon = Icons.check_circle_outline;
        break;
      case 'warn':
        statusColor = const Color(0xFFF59E0B);
        statusIcon = Icons.warning_amber_outlined;
        break;
      default:
        statusColor = const Color(0xFFEF4444);
        statusIcon = Icons.cancel_outlined;
    }
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Icon(statusIcon, color: statusColor, size: 20),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: const TextStyle(color: Colors.white60, fontSize: 11)),
                Text(value, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 13)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
