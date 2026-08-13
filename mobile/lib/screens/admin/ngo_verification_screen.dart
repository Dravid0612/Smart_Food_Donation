import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../providers/admin_provider.dart';
import '../../providers/ngo_provider.dart';
import '../../widgets/custom_card.dart';
import '../../widgets/loading_indicator.dart';
import '../../widgets/empty_state.dart';

class NgoVerificationScreen extends StatefulWidget {
  const NgoVerificationScreen({super.key});

  @override
  State<NgoVerificationScreen> createState() => _NgoVerificationScreenState();
}

class _NgoVerificationScreenState extends State<NgoVerificationScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<AdminProvider>(context, listen: false).fetchAllNgos();
    });
  }

  @override
  Widget build(BuildContext context) {
    final adminProv = Provider.of<AdminProvider>(context);
    final ngoProv = Provider.of<NgoProvider>(context);

    final allNgos = adminProv.allNgos;
    final unverifiedNgos = allNgos.where((n) => !n.isVerified).toList();

    return Scaffold(
      appBar: AppBar(
        title: const Text('NGO Verification Queue'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: adminProv.isLoading
          ? const LoadingIndicatorWidget(message: 'Loading pending NGO registrations...')
          : unverifiedNgos.isEmpty
              ? EmptyStateWidget(
                  icon: Icons.verified_user,
                  title: 'All NGOs Verified',
                  message: 'There are no pending unverified NGO registrations.',
                )
              : ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: unverifiedNgos.length,
                  itemBuilder: (context, index) {
                    final ngo = unverifiedNgos[index];
                    return CustomCard(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const CircleAvatar(
                                backgroundColor: Color(0xFFFEF3C7),
                                child: Icon(Icons.business, color: Colors.amber),
                              ),
                              const SizedBox(width: 14),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(ngo.organizationName, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                                    Text('Capacity: ${ngo.capacity} meals • Contact: ${ngo.contactPhone ?? "N/A"}', style: const TextStyle(fontSize: 12, color: Color(0xFF64748B))),
                                  ],
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          if (ngo.description != null) Text(ngo.description!, style: const TextStyle(fontSize: 13, color: Color(0xFF475569))),
                          const SizedBox(height: 12),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.end,
                            children: [
                              ElevatedButton.icon(
                                onPressed: () async {
                                  final ok = await ngoProv.verifyNgo(ngo.id);
                                  if (ok && mounted) {
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(content: Text('NGO "${ngo.organizationName}" successfully verified! 🎉'), backgroundColor: const Color(0xFF10B981)),
                                    );
                                    await adminProv.fetchAllNgos();
                                  }
                                },
                                icon: const Icon(Icons.check_circle_outline),
                                label: const Text('Verify Organization'),
                              ),
                            ],
                          ),
                        ],
                      ),
                    );
                  },
                ),
    );
  }
}
