import 'package:flutter/material.dart';

class StepItem {
  final String title;
  final String subtitle;
  final StepState state;

  const StepItem({
    required this.title,
    required this.subtitle,
    required this.state,
  });
}

enum StepState { completed, active, pending }

/// A vertical step progress indicator used in donation timelines and volunteer task flow.
class StepProgressWidget extends StatelessWidget {
  final List<StepItem> steps;

  const StepProgressWidget({super.key, required this.steps});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: List.generate(steps.length, (index) {
        final step = steps[index];
        final isLast = index == steps.length - 1;
        return IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Icon + connector column
              SizedBox(
                width: 32,
                child: Column(
                  children: [
                    _buildIcon(step.state),
                    if (!isLast)
                      Expanded(
                        child: Container(
                          width: 2,
                          color: step.state == StepState.completed
                              ? const Color(0xFF10B981)
                              : Colors.grey.shade200,
                        ),
                      ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              // Content
              Expanded(
                child: Padding(
                  padding: EdgeInsets.only(bottom: isLast ? 0 : 20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        step.title,
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 14,
                          color: step.state == StepState.pending
                              ? Colors.grey
                              : const Color(0xFF1E293B),
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        step.subtitle,
                        style: TextStyle(
                          fontSize: 12,
                          color: step.state == StepState.pending
                              ? Colors.grey.shade400
                              : const Color(0xFF64748B),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        );
      }),
    );
  }

  Widget _buildIcon(StepState state) {
    switch (state) {
      case StepState.completed:
        return Container(
          width: 28,
          height: 28,
          decoration: const BoxDecoration(
            color: Color(0xFF10B981),
            shape: BoxShape.circle,
          ),
          child: const Icon(Icons.check, color: Colors.white, size: 16),
        );
      case StepState.active:
        return Container(
          width: 28,
          height: 28,
          decoration: BoxDecoration(
            color: const Color(0xFF10B981).withOpacity(0.1),
            shape: BoxShape.circle,
            border: Border.all(color: const Color(0xFF10B981), width: 2),
          ),
          child: const Center(
            child: CircleAvatar(
              radius: 5,
              backgroundColor: Color(0xFF10B981),
            ),
          ),
        );
      case StepState.pending:
        return Container(
          width: 28,
          height: 28,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(color: Colors.grey.shade300, width: 2),
          ),
        );
    }
  }
}
