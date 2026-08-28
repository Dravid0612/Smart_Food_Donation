import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/donation_provider.dart';
import '../../widgets/donation_card.dart';
import '../../widgets/loading_state_widget.dart';
import '../../widgets/empty_state_widget.dart';
import '../../widgets/role_bottom_nav.dart';

class NgoHistoryScreen extends StatefulWidget {
  const NgoHistoryScreen({super.key});

  @override
  State<NgoHistoryScreen> createState() => _NgoHistoryScreenState();
}

class _NgoHistoryScreenState extends State<NgoHistoryScreen> {
  String _selectedFilter = 'All'; // 'All', 'In-Transit', 'Delivered', 'Distributed'

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadHistory());
  }

  Future<void> _loadHistory() async {
    final prov = Provider.of<DonationProvider>(context, listen: false);
    await prov.fetchDonations();
  }

  @override
  Widget build(BuildContext context) {
    final prov = Provider.of<DonationProvider>(context);
    final allDonations = prov.donations;

    // Filter to donations relevant to NGO history
    final ngoDonations = allDonations.where((d) => d.status.toLowerCase() != 'pending').toList();

    List filteredList;
    switch (_selectedFilter) {
      case 'In-Transit':
        filteredList = ngoDonations.where((d) => ['accepted', 'volunteer_assigned', 'collected'].contains(d.status.toLowerCase())).toList();
        break;
      case 'Delivered':
        filteredList = ngoDonations.where((d) => d.status.toLowerCase() == 'delivered').toList();
        break;
      case 'Distributed':
        filteredList = ngoDonations.where((d) => d.status.toLowerCase() == 'completed').toList();
        break;
      case 'All':
      default:
        filteredList = ngoDonations;
    }

    final filterKeys = {
      'All': context.tr('view_all'),
      'In-Transit': context.tr('in_progress'),
      'Delivered': context.tr('status_delivered'),
      'Distributed': context.tr('status_completed'),
    };

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              context.tr('donation_history'),
              style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: AppTheme.textPrimary,
                letterSpacing: -0.3,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              context.tr('rescue_live_tracking'),
              style: const TextStyle(
                fontSize: 12,
                color: AppTheme.textSecondary,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: context.tr('refresh'),
            onPressed: _loadHistory,
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadHistory,
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppTheme.space16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: ['All', 'In-Transit', 'Delivered', 'Distributed'].map((filter) {
                    final isSelected = _selectedFilter == filter;
                    return Padding(
                      padding: const EdgeInsets.only(right: AppTheme.space8),
                      child: FilterChip(
                        label: Text(filterKeys[filter] ?? filter),
                        selected: isSelected,
                        onSelected: (_) => setState(() => _selectedFilter = filter),
                        backgroundColor: AppTheme.card,
                        selectedColor: AppTheme.primaryGreen.withValues(alpha: 0.2),
                        labelStyle: TextStyle(
                          color: isSelected ? AppTheme.primaryGreen : AppTheme.textSecondary,
                          fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                          fontSize: 13,
                        ),
                      ),
                    );
                  }).toList(),
                ),
              ),
              const SizedBox(height: AppTheme.space16),

              if (prov.isLoading)
                LoadingStateWidget(message: context.tr('processing'))
              else if (filteredList.isEmpty)
                EmptyStateWidget(
                  title: context.tr('no_donations'),
                  description: context.tr('no_donations_desc'),
                  icon: Icons.receipt_long_outlined,
                  actionLabel: context.tr('active_rescues'),
                  onAction: () => context.go('/ngo'),
                )
              else
                ...filteredList.map((donation) => Padding(
                      padding: const EdgeInsets.only(bottom: AppTheme.space12),
                      child: DonationCard(
                        donation: donation,
                        currentRole: 'ngo',
                        onTap: () {
                          if (['delivered', 'completed'].contains(donation.status.toLowerCase())) {
                            context.push('/ngo/distribution/${donation.id}');
                          } else if (['accepted', 'volunteer_assigned', 'collected'].contains(donation.status.toLowerCase())) {
                            context.push('/ngo/receiving/${donation.id}');
                          }
                        },
                      ),
                    )),
            ],
          ),
        ),
      ),
      bottomNavigationBar: const RoleBottomNav(
        currentRole: 'ngo',
        currentIndex: 2, // History is tab index 2
      ),
    );
  }
}
