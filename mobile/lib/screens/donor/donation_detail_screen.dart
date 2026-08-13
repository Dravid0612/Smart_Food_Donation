import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../providers/donation_provider.dart';
import '../../widgets/status_chip.dart';
import '../../widgets/urgency_chip.dart';
import '../../widgets/custom_card.dart';
import '../../widgets/map_widget.dart';
import '../../widgets/loading_indicator.dart';

class DonationDetailScreen extends StatefulWidget {
  final int donationId;
  const DonationDetailScreen({super.key, required this.donationId});

  @override
  State<DonationDetailScreen> createState() => _DonationDetailScreenState();
}

class _DonationDetailScreenState extends State<DonationDetailScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<DonationProvider>(context, listen: false).fetchDonationDetail(widget.donationId);
    });
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
                  // Image Banner
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

                  // Title & Urgency
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

                  // Description
                  if (item.description != null && item.description!.isNotEmpty) ...[
                    CustomCard(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Description', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                          const SizedBox(height: 4),
                          Text(item.description!, style: const TextStyle(color: Color(0xFF475569))),
                        ],
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],

                  // Timeline Progress
                  const Text('Donation Timeline', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 12),
                  CustomCard(
                    child: Column(
                      children: [
                        _buildTimelineStep('Donation Created', true, 'Posted to community network'),
                        _buildTimelineStep('NGO Accepted', _isStepPassed(item.status, ['accepted', 'volunteer_assigned', 'collected', 'delivered', 'completed']), item.ngoName != null ? 'Accepted by ${item.ngoName}' : 'Waiting for NGO acceptance'),
                        _buildTimelineStep('Volunteer Assigned', _isStepPassed(item.status, ['volunteer_assigned', 'collected', 'delivered', 'completed']), item.volunteerName != null ? 'Assigned to ${item.volunteerName}' : 'Pending assignment'),
                        _buildTimelineStep('Food Collected', _isStepPassed(item.status, ['collected', 'delivered', 'completed']), 'Picked up from donor location'),
                        _buildTimelineStep('Food Delivered & Completed', _isStepPassed(item.status, ['delivered', 'completed']), 'Received by beneficiary organization'),
                      ],
                    ),
                  ),
                  const SizedBox(height: 20),

                  // Pickup Location & Map
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

  bool _isStepPassed(String currentStatus, List<String> passedStatuses) {
    return passedStatuses.contains(currentStatus.toLowerCase());
  }

  Widget _buildTimelineStep(String title, bool isCompleted, String subtitle) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Row(
        children: [
          Icon(
            isCompleted ? Icons.check_circle : Icons.radio_button_unchecked,
            color: isCompleted ? const Color(0xFF10B981) : Colors.grey.shade400,
            size: 24,
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    color: isCompleted ? const Color(0xFF1E293B) : Colors.grey,
                  ),
                ),
                Text(
                  subtitle,
                  style: TextStyle(fontSize: 12, color: isCompleted ? const Color(0xFF64748B) : Colors.grey.shade400),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
