import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/app_state.dart';

class DonationHistoryPage extends StatefulWidget {
  const DonationHistoryPage({super.key});

  @override
  State<DonationHistoryPage> createState() => _DonationHistoryPageState();
}

class _DonationHistoryPageState extends State<DonationHistoryPage> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final auth = context.read<AuthProvider>();
      context.read<DonationProvider>().loadDonations(auth.token ?? '');
    });
  }

  @override
  Widget build(BuildContext context) {
    final donationProvider = context.watch<DonationProvider>();
    return Scaffold(
      appBar: AppBar(title: const Text('Donation History')),
      body: donationProvider.isLoading
          ? const Center(child: CircularProgressIndicator())
          : donationProvider.donations.isEmpty
              ? Center(child: Text(donationProvider.errorMessage ?? 'You have not created any donations yet.'))
          : ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: donationProvider.donations.length,
              itemBuilder: (context, index) {
                final item = donationProvider.donations[index];
                return Card(
                  child: ListTile(
                    title: Text(item['food_name'] ?? 'Donation'),
                    subtitle: Text(item['status'] ?? 'pending'),
                    trailing: const Icon(Icons.chevron_right),
                  ),
                );
              },
            ),
    );
  }
}
