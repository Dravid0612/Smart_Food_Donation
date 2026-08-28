import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../core/localization/app_locale.dart';
import '../../providers/volunteer_task_provider.dart';
import '../../providers/donation_provider.dart';
import '../../widgets/custom_card.dart';
import '../../widgets/urgency_chip.dart';
import '../../widgets/loading_indicator.dart';
import '../../core/utils/food_rescue_status_helper.dart';

/// Shown when a volunteer receives or browses a pickup request.
/// Displays full donation context: food info, donor & NGO distances, urgency.
class VolunteerPickupRequestScreen extends StatefulWidget {
  final int donationId;
  const VolunteerPickupRequestScreen({super.key, required this.donationId});

  @override
  State<VolunteerPickupRequestScreen> createState() => _VolunteerPickupRequestScreenState();
}

class _VolunteerPickupRequestScreenState extends State<VolunteerPickupRequestScreen> {
  bool _isAccepting = false;
  bool _isRejecting = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<DonationProvider>(context, listen: false)
          .fetchDonationDetail(widget.donationId);
    });
  }

  Future<void> _accept() async {
    setState(() => _isAccepting = true);
    final prov = Provider.of<VolunteerTaskProvider>(context, listen: false);
    final ok = await prov.acceptPickupRequest(widget.donationId);
    if (!mounted) return;
    setState(() => _isAccepting = false);
    if (ok) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('✅ ${context.tr('accept_pickup')}!'), backgroundColor: const Color(0xFF10B981)),
      );
      context.go('/volunteer/task/${widget.donationId}');
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(prov.errorMessage != null ? context.trError(prov.errorMessage!) : context.trError('err_server')), backgroundColor: Colors.redAccent),
      );
    }
  }

  Future<void> _reject() async {
    setState(() => _isRejecting = true);
    await Provider.of<VolunteerTaskProvider>(context, listen: false)
        .rejectPickupRequest(widget.donationId);
    if (!mounted) return;
    setState(() => _isRejecting = false);
    context.pop();
  }

  @override
  Widget build(BuildContext context) {
    final prov = Provider.of<DonationProvider>(context);
    final item = prov.currentDetail;

    // Simulated distances (would come from GPS + backend in production)
    const donorDistance = '1.4 km';
    const ngoDistance = '3.2 km';

    return Scaffold(
      appBar: AppBar(
        title: Text(context.tr('active_rescues')),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: prov.isLoading || item == null
          ? LoadingIndicatorWidget(message: context.tr('processing'))
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // ── NEW REQUEST Banner ─────────────────────────────────
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFEF3C7),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: const Color(0xFFF59E0B)),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.notifications_active, color: Color(0xFFD97706)),
                        const SizedBox(width: 8),
                        Text(context.tr('active_rescues').toUpperCase(),
                            style: const TextStyle(color: Color(0xFFB45309), fontWeight: FontWeight.bold, fontSize: 13)),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),

                  // ── Food Name & Urgency ────────────────────────────────
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(
                        child: Text(context.trFood(item.foodName),
                            style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
                      ),
                      UrgencyChip(
                        urgency: item.urgencyLevel,
                        remainingMinutes: item.remainingMinutes ??
                            FoodRescueStatusHelper.calculateRemainingMinutes(item.expiryTime),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text('🍱  ${item.quantity.toInt()} ${context.trUnit(item.quantityUnit)} • ${context.trCategory(item.foodCategory)}',
                      style: const TextStyle(fontSize: 15, color: Color(0xFF475569))),
                  const SizedBox(height: 20),

                  // ── Route Card ─────────────────────────────────────────
                  CustomCard(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      children: [
                        // Donor
                        Row(
                          children: [
                            Container(
                              width: 40, height: 40,
                              decoration: const BoxDecoration(color: Color(0xFFEFF6FF), shape: BoxShape.circle),
                              child: const Icon(Icons.store, color: Colors.blue, size: 20),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(context.tr('pickup_address').toUpperCase(), style: const TextStyle(fontSize: 10, color: Color(0xFF94A3B8), fontWeight: FontWeight.bold)),
                                  Text(item.pickupAddress, style: const TextStyle(fontWeight: FontWeight.w600), overflow: TextOverflow.ellipsis),
                                ],
                              ),
                            ),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                              decoration: BoxDecoration(color: Colors.blue.shade50, borderRadius: BorderRadius.circular(20)),
                              child: const Text(donorDistance, style: TextStyle(color: Colors.blue, fontWeight: FontWeight.bold, fontSize: 12)),
                            ),
                          ],
                        ),
                        Padding(
                          padding: const EdgeInsets.only(left: 20, top: 4, bottom: 4),
                          child: Column(
                            children: List.generate(3, (_) => const Padding(
                              padding: EdgeInsets.symmetric(vertical: 1),
                              child: CircleAvatar(radius: 2, backgroundColor: Colors.grey),
                            )),
                          ),
                        ),
                        // NGO
                        Row(
                          children: [
                            Container(
                              width: 40, height: 40,
                              decoration: const BoxDecoration(color: Color(0xFFECFDF5), shape: BoxShape.circle),
                              child: const Icon(Icons.location_on, color: Color(0xFF10B981), size: 20),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(context.tr('role_ngo').toUpperCase(), style: const TextStyle(fontSize: 10, color: Color(0xFF94A3B8), fontWeight: FontWeight.bold)),
                                  Text(item.ngoName ?? context.tr('role_ngo'), style: const TextStyle(fontWeight: FontWeight.w600), overflow: TextOverflow.ellipsis),
                                ],
                              ),
                            ),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                              decoration: BoxDecoration(color: const Color(0xFFECFDF5), borderRadius: BorderRadius.circular(20)),
                              child: const Text(ngoDistance, style: TextStyle(color: Color(0xFF10B981), fontWeight: FontWeight.bold, fontSize: 12)),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),

                  // ── Urgency & Time ─────────────────────────────────────
                  CustomCard(
                    padding: const EdgeInsets.all(14),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        _infoTile('⏳ ${context.tr('remaining_time')}', _timeLeft(context, item.expiryTime), Colors.amber),
                        _infoTile('📦 ${context.tr('urgency')}', context.trUrgency(item.urgencyLevel), _urgencyColor(item.urgencyLevel)),
                        _infoTile('🍱 ${context.tr('quantity')}', '${item.quantity.toInt()} ${context.trUnit(item.quantityUnit)}', Colors.blue),
                      ],
                    ),
                  ),
                  const SizedBox(height: 28),

                  // ── Action Buttons ─────────────────────────────────────
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton(
                          onPressed: _isRejecting ? null : _reject,
                          style: OutlinedButton.styleFrom(
                            foregroundColor: Colors.redAccent,
                            side: const BorderSide(color: Colors.redAccent),
                            padding: const EdgeInsets.symmetric(vertical: 16),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                          ),
                          child: _isRejecting
                              ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.redAccent))
                              : Text(context.tr('reject').toUpperCase(), style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        flex: 2,
                        child: ElevatedButton(
                          onPressed: _isAccepting ? null : _accept,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0xFF10B981),
                            padding: const EdgeInsets.symmetric(vertical: 16),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                          ),
                          child: _isAccepting
                              ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                              : Text(context.tr('accept_pickup').toUpperCase(), style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.white)),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
    );
  }

  String _timeLeft(BuildContext context, String expiryTime) {
    try {
      final expiry = DateTime.parse(expiryTime);
      final diff = expiry.difference(DateTime.now());
      if (diff.isNegative) return context.tr('status_expired');
      if (diff.inHours > 0) return '${diff.inHours}h ${diff.inMinutes % 60}m';
      return '${diff.inMinutes}m';
    } catch (_) {
      return '2h';
    }
  }

  Color _urgencyColor(String? urgency) {
    switch (urgency?.toLowerCase()) {
      case 'urgent': return Colors.redAccent;
      case 'use soon': return Colors.amber;
      case 'fresh': return const Color(0xFF10B981);
      default: return Colors.grey;
    }
  }

  Widget _infoTile(String label, String value, Color color) {
    return Column(
      children: [
        Text(label, style: const TextStyle(fontSize: 11, color: Color(0xFF64748B))),
        const SizedBox(height: 4),
        Text(value, style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: color)),
      ],
    );
  }
}
