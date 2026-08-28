import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/localization/app_locale.dart';
import '../core/theme/app_theme.dart';
import '../providers/donation_provider.dart';

class RatingDialog extends StatefulWidget {
  final int donationId;
  final int toUserId;
  final String roleTo;
  final String targetName;

  const RatingDialog({
    super.key,
    required this.donationId,
    required this.toUserId,
    required this.roleTo,
    required this.targetName,
  });

  @override
  State<RatingDialog> createState() => _RatingDialogState();
}

class _RatingDialogState extends State<RatingDialog> {
  int _selectedRating = 5;
  final TextEditingController _feedbackController = TextEditingController();
  final Set<String> _selectedTags = {};
  bool _isSubmitting = false;

  final List<String> _availableTags = [
    'On-time',
    'Dignified Handover',
    'Great Packaging',
    'Clear Communication',
    'Safe Transport',
    'Highly Recommended',
  ];

  @override
  void dispose() {
    _feedbackController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() => _isSubmitting = true);
    final provider = Provider.of<DonationProvider>(context, listen: false);
    final success = await provider.submitRating(
      donationId: widget.donationId,
      toUserId: widget.toUserId,
      roleTo: widget.roleTo,
      ratingScore: _selectedRating,
      feedback: _feedbackController.text.trim(),
      tags: _selectedTags.join(', '),
    );
    setState(() => _isSubmitting = false);
    if (mounted) {
      Navigator.of(context).pop(success);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(success ? context.tr('success') : context.tr('error')),
          backgroundColor: success ? AppTheme.primaryGreen : AppTheme.error,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFFF59E0B).withValues(alpha: 0.15),
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.star, color: Color(0xFFF59E0B), size: 36),
              ),
              const SizedBox(height: 12),
              Text(
                '${context.tr('rate_experience')} • ${widget.targetName}',
                style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 4),
              Text(
                context.tr('rating_feedback_hint'),
                style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),

              // Star selection
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: List.generate(5, (index) {
                  final starNum = index + 1;
                  return IconButton(
                    iconSize: 36,
                    icon: Icon(
                      starNum <= _selectedRating ? Icons.star : Icons.star_border,
                      color: const Color(0xFFF59E0B),
                    ),
                    onPressed: () => setState(() => _selectedRating = starNum),
                  );
                }),
              ),
              const SizedBox(height: 12),

              // Tags
              Wrap(
                spacing: 8,
                runSpacing: 6,
                alignment: WrapAlignment.center,
                children: _availableTags.map((tag) {
                  final isSelected = _selectedTags.contains(tag);
                  return FilterChip(
                    label: Text(tag, style: TextStyle(fontSize: 11, color: isSelected ? Colors.white : Colors.black87)),
                    selected: isSelected,
                    selectedColor: AppTheme.primaryGreen,
                    onSelected: (selected) {
                      setState(() {
                        if (selected) {
                          _selectedTags.add(tag);
                        } else {
                          _selectedTags.remove(tag);
                        }
                      });
                    },
                  );
                }).toList(),
              ),
              const SizedBox(height: 12),

              // Optional feedback input
              TextField(
                controller: _feedbackController,
                maxLines: 2,
                decoration: InputDecoration(
                  hintText: context.tr('rating_feedback_hint'),
                  hintStyle: const TextStyle(fontSize: 12),
                  filled: true,
                  fillColor: Colors.grey.shade100,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: BorderSide.none,
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Actions
              Row(
                children: [
                  Expanded(
                    child: TextButton(
                      onPressed: () => Navigator.of(context).pop(false),
                      child: Text(context.tr('skip')),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.primaryGreen,
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      onPressed: _isSubmitting ? null : _submit,
                      child: _isSubmitting
                          ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                          : Text(context.tr('submit')),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
