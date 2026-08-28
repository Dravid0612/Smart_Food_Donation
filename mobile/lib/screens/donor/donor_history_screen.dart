import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/donation_provider.dart';
import '../../widgets/donation_card.dart';
import '../../widgets/skeleton_loader.dart';
import '../../widgets/empty_state_widget.dart';
import '../../widgets/role_bottom_nav.dart';

class DonorHistoryScreen extends StatefulWidget {
  const DonorHistoryScreen({super.key});

  @override
  State<DonorHistoryScreen> createState() => _DonorHistoryScreenState();
}

class _DonorHistoryScreenState extends State<DonorHistoryScreen> {
  String _selectedFilter = 'All'; // 'All', 'Active', 'Completed', 'Cancelled'

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadHistory();
    });
  }

  Future<void> _loadHistory() async {
    final prov = Provider.of<DonationProvider>(context, listen: false);
    await prov.fetchDonations(myDonationsOnly: true);
  }

  @override
  Widget build(BuildContext context) {
    final prov = Provider.of<DonationProvider>(context);
    final myDonations = prov.donations;

    List filteredList;
    switch (_selectedFilter) {
      case 'Active':
        filteredList = myDonations.where((d) => ['pending', 'accepted', 'volunteer_assigned', 'collected'].contains(d.status.toLowerCase())).toList();
        break;
      case 'Completed':
        filteredList = myDonations.where((d) => ['completed', 'delivered'].contains(d.status.toLowerCase())).toList();
        break;
      case 'Cancelled':
        filteredList = myDonations.where((d) => ['cancelled', 'expired', 'pickup_failed'].contains(d.status.toLowerCase())).toList();
        break;
      case 'All':
      default:
        filteredList = myDonations;
    }

    final filterKeys = {
      'All': context.tr('view_all'),
      'Active': context.tr('in_progress'),
      'Completed': context.tr('status_completed'),
      'Cancelled': context.tr('status_cancelled'),
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
              // Filter Chips
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: ['All', 'Active', 'Completed', 'Cancelled'].map((filter) {
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

              if (prov.isLoading && myDonations.isEmpty)
                const Column(
                  children: [
                    DonationCardSkeleton(),
                    DonationCardSkeleton(),
                    DonationCardSkeleton(),
                  ],
                )
              else if (filteredList.isEmpty)
                EmptyStateWidget(
                  title: context.tr('no_donations'),
                  description: context.tr('no_donations_desc'),
                  icon: Icons.history_edu_outlined,
                  actionLabel: context.tr('donate_now').toUpperCase(),
                  onAction: () => context.push('/donor/create'),
                )
              else
                ...filteredList.map((donation) => Padding(
                      padding: const EdgeInsets.only(bottom: AppTheme.space12),
                      child: DonationCard(
                        donation: donation,
                        currentRole: 'donor',
                        onTap: () => context.push('/donor/detail/${donation.id}'),
                      ),
                    )),
            ],
          ),
        ),
      ),
      bottomNavigationBar: const RoleBottomNav(
        currentRole: 'donor',
        currentIndex: 2, // History is tab index 2
      ),
    );
  }
}
