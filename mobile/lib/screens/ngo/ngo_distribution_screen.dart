import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../../providers/donation_provider.dart';
import '../../widgets/custom_card.dart';
import '../../widgets/loading_indicator.dart';

class NgoDistributionScreen extends StatefulWidget {
  final int donationId;
  const NgoDistributionScreen({super.key, required this.donationId});

  @override
  State<NgoDistributionScreen> createState() => _NgoDistributionScreenState();
}

class _NgoDistributionScreenState extends State<NgoDistributionScreen> {
  final _distributedController = TextEditingController();
  final _locationController = TextEditingController();
  final _beneficiariesController = TextEditingController();
  bool _isSubmitting = false;

  // Simulated previous distributions for this donation
  final List<Map<String, dynamic>> _distributions = [];
  int _totalReceived = 80;
  int _totalDistributed = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final prov = Provider.of<DonationProvider>(context, listen: false);
      prov.fetchDonationDetail(widget.donationId).then((_) {
        if (prov.currentDetail != null && mounted) {
          setState(() => _totalReceived = prov.currentDetail!.quantity.toInt());
        }
      });
    });
  }

  @override
  void dispose() {
    _distributedController.dispose();
    _locationController.dispose();
    _beneficiariesController.dispose();
    super.dispose();
  }

  Future<void> _recordDistribution() async {
    final qty = int.tryParse(_distributedController.text.trim()) ?? 0;
    if (qty <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Enter a valid quantity to distribute'), backgroundColor: Colors.redAccent),
      );
      return;
    }
    final remaining = _totalReceived - _totalDistributed;
    if (qty > remaining) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Cannot distribute more than remaining ($remaining)'),
          backgroundColor: Colors.redAccent,
        ),
      );
      return;
    }

    setState(() => _isSubmitting = true);
    await Future.delayed(const Duration(milliseconds: 800)); // API call placeholder

    setState(() {
      _distributions.add({
        'qty': qty,
        'location': _locationController.text.trim().isEmpty ? 'Community Center' : _locationController.text.trim(),
        'beneficiaries': int.tryParse(_beneficiariesController.text.trim()) ?? qty,
        'time': DateTime.now(),
      });
      _totalDistributed += qty;
      _isSubmitting = false;
      _distributedController.clear();
      _locationController.clear();
      _beneficiariesController.clear();
    });

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('✅ $qty meals recorded as distributed!'),
          backgroundColor: const Color(0xFF10B981),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final prov = Provider.of<DonationProvider>(context);
    final remaining = _totalReceived - _totalDistributed;
    final progress = _totalReceived > 0 ? _totalDistributed / _totalReceived : 0.0;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Distribution Management'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: prov.isLoading
          ? const LoadingIndicatorWidget(message: 'Loading...')
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Distribution overview
                  Container(
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [Color(0xFF047857), Color(0xFF10B981)],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Distribution Progress', style: TextStyle(color: Colors.white70, fontSize: 13)),
                        const SizedBox(height: 12),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceAround,
                          children: [
                            _statBlock('$_totalReceived', 'Total\nReceived', Colors.white),
                            _statBlock('$_totalDistributed', 'Distributed', const Color(0xFF6EE7B7)),
                            _statBlock('$remaining', 'Remaining', remaining > 0 ? Colors.amber : const Color(0xFF6EE7B7)),
                          ],
                        ),
                        const SizedBox(height: 16),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(6),
                          child: LinearProgressIndicator(
                            value: progress.clamp(0.0, 1.0),
                            backgroundColor: Colors.white24,
                            valueColor: const AlwaysStoppedAnimation<Color>(Colors.white),
                            minHeight: 10,
                          ),
                        ),
                        const SizedBox(height: 6),
                        Text(
                          '${(progress * 100).toInt()}% distributed',
                          style: const TextStyle(color: Colors.white70, fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 24),

                  const Text('Record New Distribution', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 16),

                  TextFormField(
                    controller: _distributedController,
                    keyboardType: TextInputType.number,
                    decoration: InputDecoration(
                      labelText: 'Meals Distributed *',
                      hintText: 'Remaining: $remaining meals',
                      prefixIcon: const Icon(Icons.restaurant_outlined),
                    ),
                  ),
                  const SizedBox(height: 12),

                  TextFormField(
                    controller: _locationController,
                    decoration: const InputDecoration(
                      labelText: 'Distribution Location',
                      hintText: 'e.g. Community Center, Shelter',
                      prefixIcon: Icon(Icons.location_on_outlined),
                    ),
                  ),
                  const SizedBox(height: 12),

                  TextFormField(
                    controller: _beneficiariesController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Beneficiaries Served',
                      hintText: 'Number of people served',
                      prefixIcon: Icon(Icons.people_outline),
                    ),
                  ),
                  const SizedBox(height: 20),

                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: _isSubmitting || remaining == 0 ? null : _recordDistribution,
                      icon: _isSubmitting
                          ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                          : const Icon(Icons.add_task),
                      label: Text(remaining == 0 ? 'All Meals Distributed!' : 'Record Distribution'),
                    ),
                  ),

                  if (_distributions.isNotEmpty) ...[
                    const SizedBox(height: 28),
                    const Text('Distribution History', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 12),
                    ..._distributions.reversed.map((d) => CustomCard(
                          child: Row(
                            children: [
                              Container(
                                width: 48,
                                height: 48,
                                decoration: const BoxDecoration(
                                  color: Color(0xFFECFDF5),
                                  shape: BoxShape.circle,
                                ),
                                child: const Icon(Icons.check, color: Color(0xFF10B981)),
                              ),
                              const SizedBox(width: 14),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text('${d['qty']} meals at ${d['location']}',
                                        style: const TextStyle(fontWeight: FontWeight.bold)),
                                    Text(
                                      '${d['beneficiaries']} people served • ${DateFormat('hh:mm a').format(d['time'] as DateTime)}',
                                      style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        )),
                  ],
                ],
              ),
            ),
    );
  }

  Widget _statBlock(String value, String label, Color color) {
    return Column(
      children: [
        Text(value, style: TextStyle(color: color, fontSize: 28, fontWeight: FontWeight.bold)),
        Text(label, style: const TextStyle(color: Colors.white60, fontSize: 11), textAlign: TextAlign.center),
      ],
    );
  }
}
