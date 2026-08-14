import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../../providers/donation_provider.dart';
import '../../widgets/custom_card.dart';
import '../../widgets/loading_indicator.dart';

class NgoReceivingScreen extends StatefulWidget {
  final int donationId;
  const NgoReceivingScreen({super.key, required this.donationId});

  @override
  State<NgoReceivingScreen> createState() => _NgoReceivingScreenState();
}

class _NgoReceivingScreenState extends State<NgoReceivingScreen> {
  final _formKey = GlobalKey<FormState>();
  final _quantityReceivedController = TextEditingController();
  final _damagedController = TextEditingController(text: '0');
  final _notesController = TextEditingController();
  String _conditionOnArrival = 'Good';
  bool _isSubmitting = false;

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
    _quantityReceivedController.dispose();
    _damagedController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  Future<void> _confirmDelivery() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _isSubmitting = true);

    final prov = Provider.of<DonationProvider>(context, listen: false);
    final ok = await prov.deliverDonation(widget.donationId);

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    if (ok) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('✅ Delivery confirmed! Donation marked as completed.'),
          backgroundColor: Color(0xFF10B981),
        ),
      );
      context.go('/ngo');
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Failed to confirm delivery. Try again.'), backgroundColor: Colors.redAccent),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final prov = Provider.of<DonationProvider>(context);
    final item = prov.currentDetail;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Confirm Food Receipt'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: prov.isLoading || item == null
          ? const LoadingIndicatorWidget(message: 'Loading donation...')
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Summary card
                    CustomCard(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(item.foodName, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                          const SizedBox(height: 4),
                          Text(
                            '${item.quantity.toInt()} ${item.quantityUnit} • ${item.foodCategory}',
                            style: const TextStyle(color: Color(0xFF64748B)),
                          ),
                          const SizedBox(height: 8),
                          Row(
                            children: [
                              const Icon(Icons.person_outline, size: 16, color: Color(0xFF64748B)),
                              const SizedBox(width: 4),
                              Text(
                                'Volunteer: ${item.volunteerName ?? "Unknown"}',
                                style: const TextStyle(fontSize: 13, color: Color(0xFF64748B)),
                              ),
                            ],
                          ),
                          const SizedBox(height: 4),
                          Text(
                            'Delivery Time: ${DateFormat('MMM dd, hh:mm a').format(DateTime.now())}',
                            style: const TextStyle(fontSize: 12, color: Color(0xFF94A3B8)),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 20),

                    const Text('Confirm Receipt Details', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 16),

                    // Quantity received
                    TextFormField(
                      controller: _quantityReceivedController,
                      keyboardType: TextInputType.number,
                      decoration: InputDecoration(
                        labelText: 'Quantity Received *',
                        hintText: 'Expected: ${item.quantity.toInt()} ${item.quantityUnit}',
                        prefixIcon: const Icon(Icons.inventory_2_outlined),
                      ),
                      validator: (v) {
                        if (v == null || v.trim().isEmpty) return 'Enter quantity received';
                        final n = double.tryParse(v);
                        if (n == null || n <= 0) return 'Must be > 0';
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),

                    // Damaged / missing
                    TextFormField(
                      controller: _damagedController,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        labelText: 'Damaged / Missing Quantity',
                        prefixIcon: Icon(Icons.warning_amber_outlined),
                      ),
                    ),
                    const SizedBox(height: 16),

                    // Condition on arrival
                    const Text('Condition on Arrival', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                    const SizedBox(height: 8),
                    Row(
                      children: ['Good', 'Fair', 'Poor'].map((c) {
                        final isSelected = _conditionOnArrival == c;
                        Color chipColor;
                        switch (c) {
                          case 'Good': chipColor = const Color(0xFF10B981); break;
                          case 'Fair': chipColor = const Color(0xFFF59E0B); break;
                          default: chipColor = const Color(0xFFEF4444);
                        }
                        return Padding(
                          padding: const EdgeInsets.only(right: 10),
                          child: ChoiceChip(
                            label: Text(c),
                            selected: isSelected,
                            selectedColor: chipColor.withOpacity(0.15),
                            side: BorderSide(color: isSelected ? chipColor : Colors.grey.shade300),
                            labelStyle: TextStyle(
                              color: isSelected ? chipColor : const Color(0xFF64748B),
                              fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                            ),
                            onSelected: (_) => setState(() => _conditionOnArrival = c),
                          ),
                        );
                      }).toList(),
                    ),
                    const SizedBox(height: 16),

                    // Notes
                    TextFormField(
                      controller: _notesController,
                      maxLines: 3,
                      decoration: const InputDecoration(
                        labelText: 'Additional Notes (Optional)',
                        hintText: 'Any remarks about the delivery...',
                      ),
                    ),
                    const SizedBox(height: 28),

                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        onPressed: _isSubmitting ? null : _confirmDelivery,
                        icon: _isSubmitting
                            ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                            : const Icon(Icons.task_alt),
                        label: const Text('Confirm Delivery Received'),
                      ),
                    ),
                    const SizedBox(height: 12),
                    SizedBox(
                      width: double.infinity,
                      child: OutlinedButton.icon(
                        onPressed: () => context.go('/ngo/distribution/${widget.donationId}'),
                        icon: const Icon(Icons.people_outline),
                        label: const Text('Record Distribution'),
                      ),
                    ),
                  ],
                ),
              ),
            ),
    );
  }
}
