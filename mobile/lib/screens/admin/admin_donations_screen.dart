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
  String _selectedStatusFilter = 'All'; // All, Pending, Accepted, In Transit, Delivered, Completed, Cancelled
  String _selectedUrgencyFilter = 'All'; // All, Fresh, Approaching, Urgent, Critical
  String _selectedCategoryFilter = 'All'; // All, Cooked Food, Raw Ingredients, Packaged Food, Bakery, Fresh Produce
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

    // 1. Filter by Status, Urgency, Category, and Multi-field Search
    var filteredList = donations.where((d) {
      // Status filter
      if (_selectedStatusFilter != 'All') {
        final st = d.status.toLowerCase();
        switch (_selectedStatusFilter) {
          case 'Pending':
            if (st != 'pending') return false;
            break;
          case 'Accepted':
            if (st != 'accepted' && st != 'volunteer_assigned') return false;
            break;
          case 'In Transit':
            if (!['on_the_way', 'arrived', 'collected', 'in_transit'].contains(st)) return false;
            break;
          case 'Delivered':
            if (st != 'delivered' && st != 'partially_distributed') return false;
            break;
          case 'Completed':
            if (st != 'completed') return false;
            break;
          case 'Cancelled':
            if (!['cancelled', 'expired', 'pickup_failed', 'delivery_failed'].contains(st)) return false;
            break;
        }
      }

      // Urgency filter
      if (_selectedUrgencyFilter != 'All') {
        if (d.urgencyLevel.toLowerCase() != _selectedUrgencyFilter.toLowerCase()) {
          return false;
        }
      }

      // Category filter
      if (_selectedCategoryFilter != 'All') {
        if (!d.foodCategory.toLowerCase().contains(_selectedCategoryFilter.toLowerCase())) {
          return false;
        }
      }

      // Search query filter (food name, category, address, donor, NGO, volunteer, date)
      if (_searchQuery.isNotEmpty) {
        final query = _searchQuery.toLowerCase();
        final name = d.foodName.toLowerCase();
        final cat = d.foodCategory.toLowerCase();
        final addr = d.pickupAddress.toLowerCase();
        final id = d.id.toString();
        final donor = (d.donorName ?? '').toLowerCase();
        final ngo = (d.ngoName ?? '').toLowerCase();
        final volunteer = (d.volunteerName ?? '').toLowerCase();
        final date = d.createdAt.toLowerCase();

        final matches = name.contains(query) ||
            cat.contains(query) ||
            addr.contains(query) ||
            id.contains(query) ||
            donor.contains(query) ||
            ngo.contains(query) ||
            volunteer.contains(query) ||
            date.contains(query);

        if (!matches) return false;
      }

      return true;
    }).toList();

    final statusFilters = ['All', 'Pending', 'Accepted', 'In Transit', 'Delivered', 'Completed', 'Cancelled'];
    final urgencyFilters = ['All', 'Fresh', 'Approaching', 'Urgent', 'Critical'];
    final categoryFilters = ['All', 'Cooked Food', 'Raw Ingredients', 'Packaged Food', 'Bakery', 'Fresh Produce'];

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(context.tr('nav_donations'), style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold)),
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
              // Search input (matching donor, NGO, volunteer, date, food, category)
              TextField(
                controller: _searchController,
                onChanged: (val) => setState(() => _searchQuery = val.trim()),
                decoration: InputDecoration(
                  hintText: 'Search donor, NGO, volunteer, food, date...',
                  prefixIcon: const Icon(Icons.search, size: 20),
                  suffixIcon: _searchQuery.isNotEmpty
                      ? IconButton(
                          icon: const Icon(Icons.clear, size: 18),
                          onPressed: () {
                            _searchController.clear();
                            setState(() => _searchQuery = '');
                          },
                        )
                      : null,
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

              // Filter Label: Status
              const Text('Status Filter:', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.textSecondary)),
              const SizedBox(height: 4),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: statusFilters.map((st) {
                    final isSelected = _selectedStatusFilter == st;
                    return Padding(
                      padding: const EdgeInsets.only(right: AppTheme.space8),
                      child: FilterChip(
                        label: Text(st),
                        selected: isSelected,
                        onSelected: (_) => setState(() => _selectedStatusFilter = st),
                        backgroundColor: AppTheme.card,
                        selectedColor: AppTheme.primaryGreen.withValues(alpha: 0.2),
                        labelStyle: TextStyle(
                          color: isSelected ? AppTheme.primaryGreen : AppTheme.textSecondary,
                          fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                          fontSize: 12,
                        ),
                      ),
                    );
                  }).toList(),
                ),
              ),
              const SizedBox(height: AppTheme.space8),

              // Filter Label: Urgency
              const Text('Urgency Filter:', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.textSecondary)),
              const SizedBox(height: 4),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: urgencyFilters.map((urg) {
                    final isSelected = _selectedUrgencyFilter == urg;
                    return Padding(
                      padding: const EdgeInsets.only(right: AppTheme.space8),
                      child: FilterChip(
                        label: Text(urg),
                        selected: isSelected,
                        onSelected: (_) => setState(() => _selectedUrgencyFilter = urg),
                        backgroundColor: AppTheme.card,
                        selectedColor: AppTheme.warning.withValues(alpha: 0.2),
                        labelStyle: TextStyle(
                          color: isSelected ? const Color(0xFFC05621) : AppTheme.textSecondary,
                          fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                          fontSize: 12,
                        ),
                      ),
                    );
                  }).toList(),
                ),
              ),
              const SizedBox(height: AppTheme.space8),

              // Filter Label: Food Category
              const Text('Category Filter:', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.textSecondary)),
              const SizedBox(height: 4),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: categoryFilters.map((cat) {
                    final isSelected = _selectedCategoryFilter == cat;
                    return Padding(
                      padding: const EdgeInsets.only(right: AppTheme.space8),
                      child: FilterChip(
                        label: Text(cat),
                        selected: isSelected,
                        onSelected: (_) => setState(() => _selectedCategoryFilter = cat),
                        backgroundColor: AppTheme.card,
                        selectedColor: AppTheme.primaryDark.withValues(alpha: 0.15),
                        labelStyle: TextStyle(
                          color: isSelected ? AppTheme.primaryDark : AppTheme.textSecondary,
                          fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                          fontSize: 12,
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
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          if (donation.quantity <= 15) ...[
                            Container(
                              margin: const EdgeInsets.only(bottom: 4),
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                              decoration: BoxDecoration(
                                color: const Color(0xFFF0FDF4),
                                borderRadius: BorderRadius.circular(4),
                                border: Border.all(color: AppTheme.primaryGreen.withValues(alpha: 0.3)),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  const Icon(Icons.directions_walk, size: 14, color: AppTheme.primaryGreen),
                                  const SizedBox(width: 4),
                                  Text(
                                    context.tr('self_pickup_preferred'),
                                    style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.primaryGreen),
                                  ),
                                ],
                              ),
                            ),
                          ],
                          DonationCard(
                            donation: donation,
                            currentRole: 'admin',
                            onTap: () => AdminRescueDetailModal.show(context, donation.id),
                            trailingAction: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                                  decoration: BoxDecoration(
                                    color: AppTheme.background,
                                    borderRadius: BorderRadius.circular(6),
                                    border: Border.all(color: AppTheme.border),
                                  ),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Row(
                                        children: [
                                          const Icon(Icons.people_alt_outlined, size: 14, color: AppTheme.textSecondary),
                                          const SizedBox(width: 6),
                                          Expanded(
                                            child: Text(
                                              'Donor: ${donation.donorName ?? "Donor"}  •  NGO: ${donation.ngoName ?? "Awaiting NGO response"}  •  Volunteer: ${donation.volunteerName ?? "Awaiting volunteer"}',
                                              style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary, fontWeight: FontWeight.w500),
                                              maxLines: 2,
                                              overflow: TextOverflow.ellipsis,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ],
                                  ),
                                ),
                                const SizedBox(height: 8),
                                Row(
                                  children: [
                                    Expanded(
                                      child: OutlinedButton.icon(
                                        onPressed: () => AdminRescueDetailModal.show(context, donation.id),
                                        icon: const Icon(Icons.visibility_outlined, size: 16),
                                        label: const Text('View'),
                                        style: OutlinedButton.styleFrom(
                                          padding: const EdgeInsets.symmetric(vertical: 8),
                                          minimumSize: const Size(0, 36),
                                        ),
                                      ),
                                    ),
                                    const SizedBox(width: 8),
                                    Expanded(
                                      child: ElevatedButton.icon(
                                        onPressed: () => AdminRescueDetailModal.show(context, donation.id),
                                        icon: const Icon(Icons.flash_on_outlined, size: 16),
                                        label: const Text('Intervene'),
                                        style: ElevatedButton.styleFrom(
                                          backgroundColor: (donation.rescueUrgencyLevel.toUpperCase() == 'CRITICAL' || donation.urgencyLevel.toLowerCase() == 'critical')
                                              ? AppTheme.error
                                              : const Color(0xFFD97706),
                                          foregroundColor: Colors.white,
                                          padding: const EdgeInsets.symmetric(vertical: 8),
                                          minimumSize: const Size(0, 36),
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    )),
            ],
          ),
        ),
      ),
      bottomNavigationBar: const RoleBottomNav(
        currentRole: 'admin',
        currentIndex: 1, // Donations is tab index 1
      ),
    );
  }
}
