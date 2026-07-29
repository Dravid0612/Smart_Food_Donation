import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/app_state.dart';
import '../auth/login_page.dart';

class NgoDashboardPage extends StatefulWidget {
  const NgoDashboardPage({super.key});

  @override
  State<NgoDashboardPage> createState() => _NgoDashboardPageState();
}

class _NgoDashboardPageState extends State<NgoDashboardPage> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final token = context.read<AuthProvider>().token;
      if (token != null) {
        context.read<DonationProvider>().loadAvailableDonations(token);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final donations = context.watch<DonationProvider>();
    return Scaffold(
      appBar: AppBar(
        title: const Text('NGO Dashboard'),
        actions: [
          IconButton(
            onPressed: () async {
              await auth.logout();
              if (context.mounted) Navigator.of(context).pushAndRemoveUntil(MaterialPageRoute(builder: (_) => const LoginPage()), (_) => false);
            },
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Available donations', style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 12),
            Text('Accept a pending donation, then mark it completed after pickup.', style: Theme.of(context).textTheme.bodyMedium),
            const SizedBox(height: 16),
            Expanded(
              child: donations.isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : donations.availableDonations.isEmpty
                      ? Center(child: Text(donations.errorMessage ?? 'No donations are available right now.'))
                      : RefreshIndicator(
                          onRefresh: () => donations.loadAvailableDonations(auth.token ?? ''),
                          child: ListView.separated(
                            itemCount: donations.availableDonations.length,
                            separatorBuilder: (_, __) => const SizedBox(height: 8),
                            itemBuilder: (context, index) {
                              final item = donations.availableDonations[index] as Map<String, dynamic>;
                              final isPending = item['status'] == 'pending';
                              return Card(
                                child: ListTile(
                                  title: Text(item['food_name']?.toString() ?? 'Donation'),
                                  subtitle: Text('${item['quantity'] ?? ''} • ${item['pickup_address'] ?? ''}\n${item['status'] ?? 'pending'}'),
                                  isThreeLine: true,
                                  trailing: FilledButton.tonal(
                                    onPressed: () async {
                                      try {
                                        await donations.updateDonationStatus(auth.token ?? '', item['id'] as int, isPending ? 'accepted' : 'completed');
                                      } catch (error) {
                                        if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.toString())));
                                      }
                                    },
                                    child: Text(isPending ? 'Accept' : 'Complete'),
                                  ),
                                ),
                              );
                            },
                          ),
                        ),
            ),
          ],
        ),
      ),
    );
  }
}
