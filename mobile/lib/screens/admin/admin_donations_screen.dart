import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/donation_provider.dart';
import '../../widgets/donation_card.dart';
import '../../widgets/loading_state_widget.dart';
import '../../widgets/empty_state_widget.dart';
import '../../widgets/role_bottom_nav.dart';
import 'admin_rescue_detail_modal.dart';

class AdminDonationsScreen extends StatefulWidget {
  const AdminDonationsScreen({super.key});

  @override
  State<AdminDonationsScreen> createState() => _AdminDonationsScreenState();
}

class _AdminDonationsScreenState extends State<AdminDonationsScreen> {
  String _selectedFilter = 'All'; // 'All', 'Urgent', 'At Risk', 'In Transit', 'Completed'
  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadData());
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
    final prov = Provider.of<DonationProvider>(context, listen: false);
    await prov.fetchDonations();
  }

  @override
  Widget build(BuildContext context) {
    final prov = Provider.of<DonationProvider>(context);
    final donations = prov.donations;

    // 1. Filter by operational tab
    List filteredList;
    switch (_selectedFilter) {
      case 'Urgent':
        filteredList = donations.where((d) =>
          d.urgencyLevel.toLowerCase() == 'urgent' ||
          (d.remainingMinutes != null && d.remainingMinutes! <= 60 && d.status.toLowerCase() != 'completed')
        ).toList();
        break;
      case 'At Risk':
        filteredList = donations.where((d) =>
          d.urgencyLevel.toLowerCase() == 'critical' ||
          ['pickup_failed', 'delivery_failed'].contains(d.status.toLowerCase()) ||
          (d.remainingMinutes != null && d.remainingMinutes! <= 30 && d.status.toLowerCase() != 'completed')
        ).toList();
        break;
      case 'In Transit':
        filteredList = donations.where((d) =>
          ['on_the_way', 'arrived', 'collected', 'in_transit', 'assigned', 'volunteer_assigned'].contains(d.status.toLowerCase())
        ).toList();
        break;
      case 'Completed':
        filteredList = donations.where((d) =>
          ['completed', 'delivered', 'partially_distributed'].contains(d.status.toLowerCase())
        ).toList();
        break;
      case 'All':
      default:
        filteredList = donations;
    }

    // 2. Filter by search query
    if (_searchQuery.isNotEmpty) {
      filteredList = filteredList.where((d) {
        final query = _searchQuery.toLowerCase();
        final name = d.foodName.toLowerCase();
        final cat = d.foodCategory.toLowerCase();
        final addr = d.pickupAddress.toLowerCase();
        final id = d.id.toString();
        return name.contains(query) || cat.contains(query) || addr.contains(query) || id.contains(query);
      }).toList();
    }

    final filterKeys = {
      'All': context.tr('view_all'),
      'Urgent': context.tr('stat_urgent'),
      'At Risk': context.tr('stat_at_risk'),
      'In Transit': context.tr('stat_in_transit'),
      'Completed': context.tr('status_completed'),
    };

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(context.tr('nav_rescues'), style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold)),
            Text(context.tr('food_rescue_operations'), style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary)),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadData,
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadData,
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppTheme.space16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Search input
              TextField(
                controller: _searchController,
                onChanged: (val) => setState(() => _searchQuery = val.trim()),
                decoration: InputDecoration(
                  hintText: context.tr('food_item'),
                  prefixIcon: const Icon(Icons.search, size: 20),
                  filled: true,
                  fillColor: AppTheme.card,
                  contentPadding: const EdgeInsets.symmetric(vertical: 0, horizontal: AppTheme.space16),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(AppTheme.radiusInput),
                    borderSide: const BorderSide(color: AppTheme.border),
                  ),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(AppTheme.radiusInput),
                    borderSide: const BorderSide(color: AppTheme.border),
                  ),
                ),
              ),
              const SizedBox(height: AppTheme.space12),

              // Filter Chips Row
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: ['All', 'Urgent', 'At Risk', 'In Transit', 'Completed'].map((filter) {
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
                  icon: Icons.inventory_2_outlined,
                )
              else
                ...filteredList.map((donation) => Padding(
                      padding: const EdgeInsets.only(bottom: AppTheme.space12),
                      child: DonationCard(
                        donation: donation,
                        currentRole: 'admin',
                        onTap: () => AdminRescueDetailModal.show(context, donation.id),
                      ),
                    )),
            ],
          ),
        ),
      ),
      bottomNavigationBar: const RoleBottomNav(
        currentRole: 'admin',
        currentIndex: 1, // Rescues is tab index 1
      ),
    );
  }
}
