import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../providers/donation_provider.dart';
import '../../widgets/custom_card.dart';
import '../../widgets/loading_state_widget.dart';
import '../../widgets/empty_state_widget.dart';

class RecurringDonationsScreen extends StatefulWidget {
  const RecurringDonationsScreen({super.key});

  @override
  State<RecurringDonationsScreen> createState() => _RecurringDonationsScreenState();
}

class _RecurringDonationsScreenState extends State<RecurringDonationsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<DonationProvider>(context, listen: false).fetchRecurringDonations();
    });
  }

  void _showCreateDialog() {
    final nameController = TextEditingController(text: 'Daily Dinner Buffet Surplus');
    final foodController = TextEditingController(text: 'Assorted Hot Buffet Meals');
    final qtyController = TextEditingController(text: '50');
    final addressController = TextEditingController(text: 'Taj Hotel, MG Road, Bangalore');
    final timeController = TextEditingController(text: '21:00');
    String selectedCategory = 'Cooked Food';
    String selectedUnit = 'Meals';
    String selectedFreq = 'Daily';

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDlgState) => AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: const Text('Create Recurring Schedule', style: TextStyle(fontWeight: FontWeight.bold)),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: nameController,
                  decoration: const InputDecoration(labelText: 'Template Name (e.g. Daily Dinner Surplus)'),
                ),
                TextField(
                  controller: foodController,
                  decoration: const InputDecoration(labelText: 'Typical Food Name'),
                ),
                Row(
                  children: [
                    Expanded(
                      flex: 2,
                      child: TextField(
                        controller: qtyController,
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(labelText: 'Typical Quantity'),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: DropdownButtonFormField<String>(
                        initialValue: selectedUnit,
                        items: ['Meals', 'Kg', 'Packets'].map((u) => DropdownMenuItem(value: u, child: Text(u))).toList(),
                        onChanged: (v) => setDlgState(() => selectedUnit = v!),
                        decoration: const InputDecoration(labelText: 'Unit'),
                      ),
                    ),
                  ],
                ),
                TextField(
                  controller: timeController,
                  decoration: const InputDecoration(labelText: 'Preferred Daily Pickup Time (e.g. 21:00)'),
                ),
                TextField(
                  controller: addressController,
                  decoration: const InputDecoration(labelText: 'Pickup Address'),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF10B981), foregroundColor: Colors.white),
              onPressed: () async {
                final qty = double.tryParse(qtyController.text.trim()) ?? 50.0;
                final prov = Provider.of<DonationProvider>(context, listen: false);
                final messenger = ScaffoldMessenger.of(context);
                final nav = Navigator.of(ctx);
                await prov.createRecurringDonation(
                  templateName: nameController.text.trim(),
                  foodName: foodController.text.trim(),
                  foodCategory: selectedCategory,
                  typicalQuantity: qty,
                  quantityUnit: selectedUnit,
                  frequency: selectedFreq,
                  preferredPickupTime: timeController.text.trim(),
                  pickupAddress: addressController.text.trim(),
                );
                if (mounted) {
                  nav.pop();
                  messenger.showSnackBar(
                    const SnackBar(content: Text('Recurring schedule saved!'), backgroundColor: Color(0xFF10B981)),
                  );
                }
              },
              child: const Text('Save Schedule'),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final donationProv = Provider.of<DonationProvider>(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Recurring Donation Profiles'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: const Color(0xFF10B981),
        foregroundColor: Colors.white,
        icon: const Icon(Icons.add),
        label: const Text('New Schedule'),
        onPressed: _showCreateDialog,
      ),
      body: donationProv.isLoading
          ? const LoadingStateWidget(message: 'Loading recurring profiles...')
          : donationProv.recurringDonations.isEmpty
              ? EmptyStateWidget(
                  title: 'No Recurring Schedules',
                  subtitle: 'Set up recurring schedules for daily surplus food from your buffet or kitchen for 1-tap instant donations.',
                  icon: Icons.repeat,
                  actionLabel: 'Create First Schedule',
                  onAction: _showCreateDialog,
                )
              : ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: donationProv.recurringDonations.length,
                  itemBuilder: (context, index) {
                    final item = donationProv.recurringDonations[index];
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 16),
                      child: CustomCard(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                  decoration: BoxDecoration(
                                    color: const Color(0xFF10B981).withValues(alpha: 0.15),
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  child: Text(
                                    '🔄 ${item.frequency} Schedule',
                                    style: const TextStyle(
                                      color: Color(0xFF10B981),
                                      fontWeight: FontWeight.bold,
                                      fontSize: 12,
                                    ),
                                  ),
                                ),
                                IconButton(
                                  icon: const Icon(Icons.delete_outline, color: Colors.grey, size: 20),
                                  onPressed: () => donationProv.deleteRecurringDonation(item.id),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                          Text(
                            item.templateName,
                            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '${item.foodName} • ${item.typicalQuantity.toStringAsFixed(0)} ${item.quantityUnit}',
                            style: TextStyle(fontSize: 14, color: Colors.grey.shade700),
                          ),
                          const SizedBox(height: 8),
                          Row(
                            children: [
                              const Icon(Icons.access_time, size: 16, color: Colors.grey),
                              const SizedBox(width: 4),
                              Text('Preferred Time: ${item.preferredPickupTime}', style: const TextStyle(fontSize: 12, color: Colors.grey)),
                              const SizedBox(width: 16),
                              const Icon(Icons.location_on, size: 16, color: Colors.grey),
                              const SizedBox(width: 4),
                              Expanded(
                                child: Text(
                                  item.pickupAddress,
                                  style: const TextStyle(fontSize: 12, color: Colors.grey),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 16),
                          SizedBox(
                            width: double.infinity,
                            child: ElevatedButton.icon(
                              style: ElevatedButton.styleFrom(
                                backgroundColor: const Color(0xFF10B981),
                                foregroundColor: Colors.white,
                                padding: const EdgeInsets.symmetric(vertical: 12),
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                              ),
                              icon: const Icon(Icons.bolt, color: Colors.white),
                              label: const Text('1-Tap: Post Today\'s Donation'),
                              onPressed: () async {
                                final messenger = ScaffoldMessenger.of(context);
                                final router = GoRouter.of(context);
                                final success = await donationProv.instantiateTodayDonation(item.id);
                                if (mounted && success) {
                                  messenger.showSnackBar(
                                    const SnackBar(
                                      content: Text('Today\'s donation has been created and verified NGOs notified!'),
                                      backgroundColor: Color(0xFF10B981),
                                    ),
                                  );
                                  router.pop();
                                }
                              },
                            ),
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
    );
  }
}
