import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/auth_provider.dart';
import '../../providers/notification_provider.dart';
import '../../widgets/custom_card.dart';
import '../../widgets/skeleton_loader.dart';
import '../../widgets/empty_state_widget.dart';

class NotificationCenterScreen extends StatefulWidget {
  const NotificationCenterScreen({super.key});

  @override
  State<NotificationCenterScreen> createState() => _NotificationCenterScreenState();
}

class _NotificationCenterScreenState extends State<NotificationCenterScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<NotificationProvider>(context, listen: false).fetchNotifications();
    });
  }

  @override
  Widget build(BuildContext context) {
    final notifProv = Provider.of<NotificationProvider>(context);
    final notifications = notifProv.notifications;

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Text(context.tr('notifications')),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        actions: [
          if (notifications.isNotEmpty)
            TextButton(
              onPressed: () => notifProv.markAllAsRead(),
              child: Text(
                context.tr('mark_all_read'),
                style: const TextStyle(fontWeight: FontWeight.w600, color: AppTheme.primaryGreen),
              ),
            ),
        ],
      ),
      body: notifProv.isLoading && notifications.isEmpty
          ? ListView(
              padding: const EdgeInsets.all(16),
              children: const [
                NotificationItemSkeleton(),
                NotificationItemSkeleton(),
                NotificationItemSkeleton(),
                NotificationItemSkeleton(),
              ],
            )
          : notifications.isEmpty
              ? EmptyStateWidget(
                  icon: Icons.notifications_off_outlined,
                  title: context.tr('no_notifications'),
                  description: context.tr('no_notifications_desc'),
                )
              : ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: notifications.length,
                  itemBuilder: (context, index) {
                    final item = notifications[index];
                    return CustomCard(
                      onTap: () {
                        notifProv.markAsRead(item.id);
                        if (item.relatedDonationId != null) {
                          final auth = Provider.of<AuthProvider>(context, listen: false);
                          final role = auth.currentUser?.role ?? 'donor';
                          final type = item.type.toLowerCase();

                          if (type == 'volunteer_arrived' && role == 'donor') {
                            context.push('/donor/otp/${item.relatedDonationId}');
                          } else if (role == 'volunteer') {
                            context.push('/volunteer/task/${item.relatedDonationId}');
                          } else if (role == 'ngo') {
                            context.push('/ngo/receiving/${item.relatedDonationId}');
                          } else {
                            context.push('/donor/detail/${item.relatedDonationId}');
                          }
                        }
                      },
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Container(
                            padding: const EdgeInsets.all(10),
                            decoration: BoxDecoration(
                              color: item.isRead ? Colors.grey.shade100 : const Color(0xFF10B981).withValues(alpha: 0.12),
                              shape: BoxShape.circle,
                            ),
                            child: Icon(
                              _getNotifIcon(item.type),
                              color: item.isRead ? Colors.grey : const Color(0xFF10B981),
                              size: 22,
                            ),
                          ),
                          const SizedBox(width: 14),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    Expanded(
                                      child: Text(
                                        item.title,
                                        style: TextStyle(
                                          fontWeight: item.isRead ? FontWeight.normal : FontWeight.bold,
                                          fontSize: 15,
                                        ),
                                      ),
                                    ),
                                    if (!item.isRead)
                                      Container(
                                        width: 8,
                                        height: 8,
                                        decoration: const BoxDecoration(color: Color(0xFF10B981), shape: BoxShape.circle),
                                      ),
                                  ],
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  item.message,
                                  style: const TextStyle(fontSize: 13, color: Color(0xFF475569)),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                ),
    );
  }

  IconData _getNotifIcon(String type) {
    switch (type.toLowerCase()) {
      case 'volunteer_arrived':
      case 'arrived':
        return Icons.location_on;
      case 'pickup_en_route':
      case 'en_route':
      case 'assignment':
        return Icons.directions_bike;
      case 'success':
      case 'collected':
      case 'delivered':
        return Icons.check_circle_outline;
      case 'donation':
      case 'created':
        return Icons.fastfood_outlined;
      default:
        return Icons.notifications_outlined;
    }
  }
}
