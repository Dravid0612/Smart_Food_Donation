import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/api/api_client.dart';
import '../../core/theme/app_theme.dart';
import '../../widgets/empty_state_widget.dart';
import '../../widgets/loading_state_widget.dart';

/// A7 Admin Audit Log Viewer Screen.
/// Read-only security and operational audit trail.
/// Displays timestamp, actor, action, resource, event details, and transition status.
class AdminAuditLogScreen extends StatefulWidget {
  final List<Map<String, dynamic>>? initialLogs;
  const AdminAuditLogScreen({super.key, this.initialLogs});

  @override
  State<AdminAuditLogScreen> createState() => _AdminAuditLogScreenState();
}

class _AdminAuditLogScreenState extends State<AdminAuditLogScreen> {
  final ApiClient _apiClient = ApiClient();
  List<Map<String, dynamic>> _logs = [];
  bool _isLoading = true;
  String _filter = 'All'; // All, Login, Rescue, OTP, Security

  @override
  void initState() {
    super.initState();
    if (widget.initialLogs != null) {
      _logs = widget.initialLogs!;
      _isLoading = false;
    } else {
      _fetchAuditLogs();
    }
  }

  Future<void> _fetchAuditLogs() async {
    setState(() => _isLoading = true);
    try {
      final res = await _apiClient.dio.get('/admin/audit-logs', queryParameters: {'limit': 100});
      if (mounted) {
        setState(() {
          _logs = (res.data as List).map((e) => Map<String, dynamic>.from(e)).toList();
          _isLoading = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  List<Map<String, dynamic>> get _filteredLogs {
    if (_filter == 'Login') {
      return _logs.where((l) => (l['action'] ?? '').toString().contains('login')).toList();
    }
    if (_filter == 'Rescue') {
      return _logs.where((l) => ['donation', 'volunteer_assignment', 'ngo'].contains(l['resource_type']) || (l['action'] ?? '').toString().contains('rescue') || (l['action'] ?? '').toString().contains('pickup')).toList();
    }
    if (_filter == 'OTP') {
      return _logs.where((l) => (l['action'] ?? '').toString().contains('otp')).toList();
    }
    if (_filter == 'Security') {
      return _logs.where((l) => l['status'] == 'blocked' || l['status'] == 'failed' || (l['action'] ?? '').toString().contains('unauthorized')).toList();
    }
    return _logs;
  }

  Color _getStatusColor(String? status) {
    switch (status?.toLowerCase()) {
      case 'success':
        return AppTheme.primaryGreen;
      case 'blocked':
        return AppTheme.criticalCrimson;
      case 'failed':
        return AppTheme.urgentAmber;
      default:
        return AppTheme.textSecondary;
    }
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _filteredLogs;

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: const Text('A7: Security Audit Log', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
        leading: IconButton(icon: const Icon(Icons.arrow_back), onPressed: () => context.pop()),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _fetchAuditLogs),
        ],
      ),
      body: _isLoading
          ? const LoadingStateWidget(message: 'Loading security audit logs...')
          : Column(
              children: [
                // Filter bar
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  color: AppTheme.card,
                  child: SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: [
                        _buildFilterChip('All', 'All Events'),
                        const SizedBox(width: 8),
                        _buildFilterChip('Rescue', 'Rescues & Assignments'),
                        const SizedBox(width: 8),
                        _buildFilterChip('OTP', 'OTP Verification'),
                        const SizedBox(width: 8),
                        _buildFilterChip('Login', 'Authentication'),
                        const SizedBox(width: 8),
                        _buildFilterChip('Security', 'Security Interventions'),
                      ],
                    ),
                  ),
                ),
                const Divider(height: 1),

                // Audit Log List
                Expanded(
                  child: filtered.isEmpty
                      ? const EmptyStateWidget(
                          icon: Icons.shield_outlined,
                          title: 'No Audit Records',
                          subtitle: 'No security or operational log entries matching the selected filter.',
                        )
                      : ListView.separated(
                          padding: const EdgeInsets.all(16),
                          itemCount: filtered.length,
                          separatorBuilder: (_, __) => const SizedBox(height: 10),
                          itemBuilder: (ctx, idx) {
                            final log = filtered[idx];
                            final status = log['status']?.toString() ?? 'success';
                            final action = log['action']?.toString() ?? 'Unknown Action';
                            final actor = log['actor']?.toString() ?? 'System';
                            final ts = log['timestamp']?.toString() ?? '';
                            final details = log['details']?.toString() ?? '';
                            final resourceType = log['resource_type']?.toString();
                            final resourceId = log['resource_id']?.toString();

                            final statusColor = _getStatusColor(status);

                            return Container(
                              padding: const EdgeInsets.all(14),
                              decoration: BoxDecoration(
                                color: AppTheme.card,
                                borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                                border: Border.all(color: AppTheme.border),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                        decoration: BoxDecoration(
                                          color: statusColor.withValues(alpha: 0.1),
                                          borderRadius: BorderRadius.circular(AppTheme.radiusPill),
                                        ),
                                        child: Text(
                                          status.toUpperCase(),
                                          style: TextStyle(
                                            fontSize: 10,
                                            fontWeight: FontWeight.bold,
                                            color: statusColor,
                                          ),
                                        ),
                                      ),
                                      const SizedBox(width: 10),
                                      Expanded(
                                        child: Text(
                                          action,
                                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: AppTheme.textPrimary),
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ),
                                      if (ts.isNotEmpty)
                                        Text(
                                          ts.length > 16 ? ts.substring(0, 16).replaceAll('T', ' ') : ts,
                                          style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary),
                                        ),
                                    ],
                                  ),
                                  const SizedBox(height: 6),
                                  Row(
                                    children: [
                                      const Icon(Icons.person_outline, size: 14, color: AppTheme.textSecondary),
                                      const SizedBox(width: 4),
                                      Text(
                                        'Actor: $actor',
                                        style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                                      ),
                                      if (resourceType != null) ...[
                                        const SizedBox(width: 12),
                                        const Icon(Icons.link, size: 14, color: AppTheme.textSecondary),
                                        const SizedBox(width: 4),
                                        Text(
                                          '$resourceType ${resourceId != null ? "#$resourceId" : ""}',
                                          style: const TextStyle(fontSize: 12, color: AppTheme.trustTeal, fontWeight: FontWeight.w600),
                                        ),
                                      ],
                                    ],
                                  ),
                                  if (details.isNotEmpty) ...[
                                    const SizedBox(height: 6),
                                    Text(
                                      details,
                                      style: TextStyle(fontSize: 12, color: Colors.grey.shade700),
                                      maxLines: 2,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ],
                                ],
                              ),
                            );
                          },
                        ),
                ),
              ],
            ),
    );
  }

  Widget _buildFilterChip(String key, String label) {
    final isSelected = _filter == key;
    return InkWell(
      onTap: () => setState(() => _filter = key),
      borderRadius: BorderRadius.circular(AppTheme.radiusPill),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected ? AppTheme.primaryGreen.withValues(alpha: 0.12) : AppTheme.background,
          borderRadius: BorderRadius.circular(AppTheme.radiusPill),
          border: Border.all(
            color: isSelected ? AppTheme.primaryGreen : AppTheme.border,
            width: isSelected ? 1.5 : 1.0,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 12,
            fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
            color: isSelected ? AppTheme.primaryGreen : AppTheme.textSecondary,
          ),
        ),
      ),
    );
  }
}
