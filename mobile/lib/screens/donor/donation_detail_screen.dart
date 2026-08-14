import 'dart:math';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../providers/donation_provider.dart';
import '../../widgets/status_chip.dart';
import '../../widgets/urgency_chip.dart';
import '../../widgets/custom_card.dart';
import '../../widgets/map_widget.dart';
import '../../widgets/loading_indicator.dart';
import '../../widgets/otp_display_widget.dart';
import '../../widgets/step_progress_widget.dart';

class DonationDetailScreen extends StatefulWidget {
  final int donationId;
  const DonationDetailScreen({super.key, required this.donationId});

  @override
  State<DonationDetailScreen> createState() => _DonationDetailScreenState();
}

class _DonationDetailScreenState extends State<DonationDetailScreen> {
  // Generate a consistent OTP per donation ID (demo only)
  late final String _pickupOtp;

  @override
  void initState() {
    super.initState();
    // Deterministic OTP based on donation ID for demo consistency
    final rng = Random(widget.donationId * 7919);
    _pickupOtp = (1000 + rng.nextInt(8999)).toString();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<DonationProvider>(context, listen: false)
          .fetchDonationDetail(widget.donationId);
    });
  }

  List<StepItem> _buildTimeline(String status, String? ngoName, String? volunteerName) {
    final s = status.toLowerCase();

    StepState _state(List<String> passedStatuses) {
      if (passedStatuses.contains(s)) return StepState.completed;
      // Check if it's the current active step
      final allStatuses = [
        'pending', 'matching', 'accepted', 'volunteer_assigned',
        'picked_up', 'collected', 'delivered', 'completed'
      ];
      final currentIndex = allStatuses.indexOf(s);
      final stepIndex = allStatuses.indexWhere((st) => passedStatuses.contains(st));
      if (stepIndex >= 0 && stepIndex == currentIndex + 1) return StepState.active;
      return StepState.pending;
    }

    return [
      StepItem(
        title: 'Donation Created',
        subtitle: 'Posted to community network',
        state: StepState.completed,
      ),
      StepItem(
        title: 'NGO Matching',
        subtitle: 'Searching for nearby NGOs by distance & capacity',
        state: _state(['accepted', 'volunteer_assigned', 'picked_up', 'collected', 'delivered', 'completed']),
      ),
      StepItem(
        title: 'NGO Accepted',
        subtitle: ngoName != null ? 'Accepted by $ngoName' : 'Waiting for NGO acceptance',
        state: _state(['volunteer_assigned', 'picked_up', 'collected', 'delivered', 'completed']),
      ),
      StepItem(
        title: 'Volunteer Assigned',
        subtitle: volunteerName != null ? 'Assigned to $volunteerName' : 'Pending assignment',
        state: _state(['picked_up', 'collected', 'delivered', 'completed']),
      ),
      StepItem(
        title: 'Pickup Started',
        subtitle: 'Volunteer en route to pickup location',
        state: _state(['collected', 'delivered', 'completed']),
      ),
      StepItem(
        title: 'Food Picked Up',
        subtitle: 'Collected from donor location',
        state: _state(['delivered', 'completed']),
      ),
      StepItem(
        title: 'Delivered to NGO',
        subtitle: 'Food handed over to NGO',
        state: _state(['completed']),
      ),
      StepItem(
        title: 'Completed',
        subtitle: 'Donation successfully completed 🎉',
        state: s == 'completed' ? StepState.completed : StepState.pending,
      ),
    ];
  }

  bool _shouldShowOtp(String status) {
    return ['volunteer_assigned', 'picked_up'].contains(status.toLowerCase());
  }

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<DonationProvider>(context);
    final item = provider.currentDetail;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Donation Details'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: provider.isLoading || item == null
          ? const LoadingIndicatorWidget(message: 'Loading donation timeline...')
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // ── Image Banner ──────────────────────────────────────
                  ClipRRect(
                    borderRadius: BorderRadius.circular(16),
                    child: Image.network(
                      item.imageUrl ?? 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=400',
                      height: 200,
                      width: double.infinity,
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => Container(
                        height: 180,
                        color: Colors.grey.shade200,
                        child: const Icon(Icons.fastfood, size: 64, color: Colors.grey),
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // ── Title & Chips ─────────────────────────────────────
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(
                        child: Text(
                          item.foodName,
                          style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                        ),
                      ),
                      UrgencyChip(urgency: item.urgencyLevel),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      StatusChip(status: item.status),
                      const SizedBox(width: 10),
                      Text(
                        '${item.quantity.toInt()} ${item.quantityUnit} • ${item.foodCategory}',
                        style: const TextStyle(color: Color(0xFF64748B), fontWeight: FontWeight.w500),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),

                  // ── Description ───────────────────────────────────────
                  if (item.description != null && item.description!.isNotEmpty) ...[
                    CustomCard(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Details', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                          const SizedBox(height: 6),
                          Text(item.description!, style: const TextStyle(color: Color(0xFF475569), fontSize: 13)),
                        ],
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],

                  // ── OTP Display (shown when volunteer is assigned) ─────
                  if (_shouldShowOtp(item.status)) ...[
                    OtpDisplayWidget(otp: _pickupOtp),
                    const SizedBox(height: 16),
                  ],

                  // ── 8-Step Donation Timeline ──────────────────────────
                  const Text('Donation Timeline', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 12),
                  CustomCard(
                    padding: const EdgeInsets.all(16),
                    child: StepProgressWidget(
                      steps: _buildTimeline(item.status, item.ngoName, item.volunteerName),
                    ),
                  ),
                  const SizedBox(height: 20),

                  // ── Pickup Location & Map ─────────────────────────────
                  const Text('Pickup Location', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  Text(item.pickupAddress, style: const TextStyle(color: Color(0xFF64748B))),
                  const SizedBox(height: 12),
                  OpenStreetMapWidget(
                    latitude: item.latitude ?? 12.9716,
                    longitude: item.longitude ?? 77.5946,
                    title: item.foodName,
                    height: 180,
                  ),
                  const SizedBox(height: 30),
                ],
              ),
            ),
    );
  }
}
