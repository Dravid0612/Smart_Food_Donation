import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../providers/volunteer_task_provider.dart';
import '../../providers/donation_provider.dart';
import '../../widgets/custom_card.dart';
import '../../widgets/loading_indicator.dart';
import '../../widgets/step_progress_widget.dart';

/// Active task screen with step-by-step pickup→delivery flow and OTP verification.
class VolunteerActiveTaskScreen extends StatefulWidget {
  final int donationId;
  const VolunteerActiveTaskScreen({super.key, required this.donationId});

  @override
  State<VolunteerActiveTaskScreen> createState() => _VolunteerActiveTaskScreenState();
}

class _VolunteerActiveTaskScreenState extends State<VolunteerActiveTaskScreen> {
  final _otpController = TextEditingController();
  bool _otpVerified = false;
  bool _otpError = false;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<DonationProvider>(context, listen: false)
          .fetchDonationDetail(widget.donationId);
    });
  }

  @override
  void dispose() {
    _otpController.dispose();
    super.dispose();
  }

  Future<void> _openMaps(double lat, double lng, String label) async {
    final uri = Uri.parse('https://www.google.com/maps/dir/?api=1&destination=$lat,$lng');
    if (await canLaunchUrl(uri)) await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  void _verifyOtp() {
    final taskProv = Provider.of<VolunteerTaskProvider>(context, listen: false);
    final isValid = taskProv.verifyPickupOtp(widget.donationId, _otpController.text.trim());
    setState(() {
      _otpVerified = isValid;
      _otpError = !isValid;
    });
    if (isValid) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('✅ OTP Verified! Pickup confirmed.'), backgroundColor: Color(0xFF10B981)),
      );
    }
  }

  Future<void> _markCollected() async {
    setState(() => _isLoading = true);
    final ok = await Provider.of<VolunteerTaskProvider>(context, listen: false)
        .markCollected(widget.donationId);
    if (!mounted) return;
    setState(() => _isLoading = false);
    if (ok) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('🍱 Food collected! Navigate to NGO.'), backgroundColor: Colors.amber),
      );
      Provider.of<DonationProvider>(context, listen: false)
          .fetchDonationDetail(widget.donationId);
    }
  }

  Future<void> _markDelivered() async {
    setState(() => _isLoading = true);
    final ok = await Provider.of<VolunteerTaskProvider>(context, listen: false)
        .markDelivered(widget.donationId);
    if (!mounted) return;
    setState(() => _isLoading = false);
    if (ok) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('✅ Delivery confirmed! Task complete.'), backgroundColor: Color(0xFF10B981)),
      );
      context.go('/volunteer');
    }
  }

  List<StepItem> _buildTaskSteps(String status) {
    final s = status.toLowerCase();
    bool done(List<String> ss) => ss.contains(s);

    return [
      StepItem(title: 'Navigate to Donor', subtitle: 'Head to pickup location', state: StepState.completed),
      StepItem(
        title: 'Arrive at Donor',
        subtitle: 'Enter the OTP shown by the donor',
        state: done(['collected', 'delivered', 'completed']) ? StepState.completed : s == 'volunteer_assigned' ? StepState.active : StepState.pending,
      ),
      StepItem(
        title: 'OTP Verified — Pickup',
        subtitle: 'Food collected from donor',
        state: done(['collected', 'delivered', 'completed']) ? StepState.completed : StepState.pending,
      ),
      StepItem(
        title: 'Navigate to NGO',
        subtitle: 'En route to delivery location',
        state: done(['delivered', 'completed']) ? StepState.completed : s == 'collected' ? StepState.active : StepState.pending,
      ),
      StepItem(
        title: 'Arrive at NGO',
        subtitle: 'NGO confirms delivery',
        state: done(['delivered', 'completed']) ? StepState.completed : StepState.pending,
      ),
      StepItem(
        title: 'Delivery Confirmed',
        subtitle: 'Task complete! Impact recorded.',
        state: s == 'delivered' || s == 'completed' ? StepState.completed : StepState.pending,
      ),
    ];
  }

  @override
  Widget build(BuildContext context) {
    final donationProv = Provider.of<DonationProvider>(context);
    final item = donationProv.currentDetail;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Active Task'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: donationProv.isLoading || item == null
          ? const LoadingIndicatorWidget(message: 'Loading task...')
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // ── Food Summary ───────────────────────────────────────
                  CustomCard(
                    child: Row(
                      children: [
                        ClipRRect(
                          borderRadius: BorderRadius.circular(10),
                          child: Image.network(
                            item.imageUrl ?? 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=400',
                            width: 64, height: 64, fit: BoxFit.cover,
                            errorBuilder: (_, __, ___) => Container(
                              width: 64, height: 64, color: Colors.grey.shade100,
                              child: const Icon(Icons.fastfood),
                            ),
                          ),
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(item.foodName, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                              Text('${item.quantity.toInt()} ${item.quantityUnit} • ${item.foodCategory}',
                                  style: const TextStyle(color: Color(0xFF64748B), fontSize: 13)),
                              Text('NGO: ${item.ngoName ?? "Assigned NGO"}',
                                  style: const TextStyle(color: Color(0xFF10B981), fontSize: 12, fontWeight: FontWeight.w600)),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 20),

                  // ── Navigation Buttons ─────────────────────────────────
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: () => _openMaps(item.latitude ?? 12.9716, item.longitude ?? 77.5946, 'Donor Pickup'),
                          icon: const Icon(Icons.directions, color: Colors.blue),
                          label: const Text('Navigate to Donor', style: TextStyle(color: Colors.blue)),
                          style: OutlinedButton.styleFrom(side: const BorderSide(color: Colors.blue)),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: () => _openMaps(12.9784, 77.6408, 'NGO Location'),
                          icon: const Icon(Icons.navigation, color: Color(0xFF10B981)),
                          label: const Text('Navigate to NGO', style: TextStyle(color: Color(0xFF10B981))),
                          style: OutlinedButton.styleFrom(side: const BorderSide(color: Color(0xFF10B981))),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),

                  // ── Task Step Progress ─────────────────────────────────
                  const Text('Task Progress', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 12),
                  CustomCard(
                    padding: const EdgeInsets.all(16),
                    child: StepProgressWidget(steps: _buildTaskSteps(item.status)),
                  ),
                  const SizedBox(height: 20),

                  // ── OTP Verification (when volunteer_assigned) ─────────
                  if (item.status.toLowerCase() == 'volunteer_assigned') ...[
                    const Text('Pickup Verification', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 12),
                    CustomCard(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Enter the 4-digit OTP shown by the donor to verify pickup.',
                              style: TextStyle(color: Color(0xFF64748B), fontSize: 13)),
                          const SizedBox(height: 16),
                          Row(
                            children: [
                              Expanded(
                                child: TextField(
                                  controller: _otpController,
                                  keyboardType: TextInputType.number,
                                  maxLength: 4,
                                  textAlign: TextAlign.center,
                                  style: const TextStyle(fontSize: 28, fontWeight: FontWeight.bold, letterSpacing: 12),
                                  decoration: InputDecoration(
                                    hintText: '——',
                                    counterText: '',
                                    errorText: _otpError ? 'Invalid OTP. Try again.' : null,
                                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                                  ),
                                ),
                              ),
                              const SizedBox(width: 12),
                              ElevatedButton(
                                onPressed: _otpVerified ? null : _verifyOtp,
                                child: const Text('Verify'),
                              ),
                            ],
                          ),
                          if (_otpVerified) ...[
                            const SizedBox(height: 12),
                            Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: const Color(0xFFECFDF5),
                                borderRadius: BorderRadius.circular(10),
                              ),
                              child: const Row(
                                children: [
                                  Icon(Icons.verified, color: Color(0xFF10B981)),
                                  SizedBox(width: 8),
                                  Text('OTP Verified! Ready to collect.',
                                      style: TextStyle(color: Color(0xFF047857), fontWeight: FontWeight.bold)),
                                ],
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                    const SizedBox(height: 16),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        onPressed: (!_otpVerified || _isLoading) ? null : _markCollected,
                        style: ElevatedButton.styleFrom(backgroundColor: Colors.amber.shade700, padding: const EdgeInsets.symmetric(vertical: 16)),
                        icon: _isLoading
                            ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                            : const Icon(Icons.shopping_bag_outlined, color: Colors.white),
                        label: const Text('Mark Food Collected', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)),
                      ),
                    ),
                  ],

                  // ── Mark Delivered (when collected) ────────────────────
                  if (item.status.toLowerCase() == 'collected') ...[
                    const SizedBox(height: 16),
                    Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: const Color(0xFFFEF3C7),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: const Color(0xFFF59E0B)),
                      ),
                      child: const Row(
                        children: [
                          Icon(Icons.local_shipping, color: Color(0xFFD97706)),
                          SizedBox(width: 8),
                          Text('In Transit — Navigate to NGO and hand over food.', style: TextStyle(color: Color(0xFFB45309))),
                        ],
                      ),
                    ),
                    const SizedBox(height: 16),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        onPressed: _isLoading ? null : _markDelivered,
                        style: ElevatedButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 16)),
                        icon: _isLoading
                            ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                            : const Icon(Icons.task_alt),
                        label: const Text('Mark Delivered to NGO', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                      ),
                    ),
                  ],
                ],
              ),
            ),
    );
  }
}
