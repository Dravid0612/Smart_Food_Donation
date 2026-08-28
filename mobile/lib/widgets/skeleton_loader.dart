import 'package:flutter/material.dart';
import '../core/theme/app_theme.dart';

/// Shimmering skeleton loader for card placeholders and data fetching states
class SkeletonLoader extends StatefulWidget {
  final double width;
  final double height;
  final double borderRadius;
  final EdgeInsetsGeometry? margin;

  const SkeletonLoader({
    super.key,
    required this.width,
    required this.height,
    this.borderRadius = AppTheme.radiusSmall,
    this.margin,
  });

  @override
  State<SkeletonLoader> createState() => _SkeletonLoaderState();
}

class _SkeletonLoaderState extends State<SkeletonLoader>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);
    _animation = Tween<double>(begin: 0.3, end: 0.8).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _animation,
      builder: (context, child) {
        return Container(
          width: widget.width,
          height: widget.height,
          margin: widget.margin,
          decoration: BoxDecoration(
            color: AppTheme.border.withValues(alpha: _animation.value),
            borderRadius: BorderRadius.circular(widget.borderRadius),
          ),
        );
      },
    );
  }
}

/// Ready-made card skeleton loader for donation feeds
class DonationCardSkeleton extends StatelessWidget {
  const DonationCardSkeleton({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: AppTheme.space12),
      padding: const EdgeInsets.all(AppTheme.space16),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
        border: Border.all(color: AppTheme.border),
      ),
      child: const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              SkeletonLoader(width: 90, height: 20, borderRadius: AppTheme.radiusSmall),
              SkeletonLoader(width: 70, height: 20, borderRadius: AppTheme.radiusSmall),
            ],
          ),
          SizedBox(height: AppTheme.space12),
          SkeletonLoader(width: double.infinity, height: 18, borderRadius: AppTheme.radiusXS),
          SizedBox(height: AppTheme.space8),
          SkeletonLoader(width: 180, height: 14, borderRadius: AppTheme.radiusXS),
          SizedBox(height: AppTheme.space16),
          Row(
            children: [
              SkeletonLoader(width: 100, height: 14, borderRadius: AppTheme.radiusXS),
              Spacer(),
              SkeletonLoader(width: 80, height: 32, borderRadius: AppTheme.radiusSmall),
            ],
          ),
        ],
      ),
    );
  }
}

/// Ready-made skeleton loader for dashboard summary cards
class DashboardStatsSkeleton extends StatelessWidget {
  const DashboardStatsSkeleton({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: AppTheme.space16),
      padding: const EdgeInsets.all(AppTheme.space16),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
        border: Border.all(color: AppTheme.border),
      ),
      child: const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              SkeletonLoader(width: 24, height: 24, borderRadius: AppTheme.radiusSmall),
              SizedBox(width: 8),
              SkeletonLoader(width: 140, height: 16, borderRadius: AppTheme.radiusXS),
            ],
          ),
          SizedBox(height: AppTheme.space16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              Column(
                children: [
                  SkeletonLoader(width: 60, height: 24, borderRadius: AppTheme.radiusSmall),
                  SizedBox(height: 4),
                  SkeletonLoader(width: 70, height: 12, borderRadius: AppTheme.radiusXS),
                ],
              ),
              Column(
                children: [
                  SkeletonLoader(width: 60, height: 24, borderRadius: AppTheme.radiusSmall),
                  SizedBox(height: 4),
                  SkeletonLoader(width: 70, height: 12, borderRadius: AppTheme.radiusXS),
                ],
              ),
              Column(
                children: [
                  SkeletonLoader(width: 60, height: 24, borderRadius: AppTheme.radiusSmall),
                  SizedBox(height: 4),
                  SkeletonLoader(width: 70, height: 12, borderRadius: AppTheme.radiusXS),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// Ready-made skeleton loader for volunteer task cards
class TaskCardSkeleton extends StatelessWidget {
  const TaskCardSkeleton({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: AppTheme.space12),
      padding: const EdgeInsets.all(AppTheme.space16),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
        border: Border.all(color: AppTheme.border),
      ),
      child: const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              SkeletonLoader(width: 120, height: 18, borderRadius: AppTheme.radiusSmall),
              SkeletonLoader(width: 60, height: 18, borderRadius: AppTheme.radiusSmall),
            ],
          ),
          SizedBox(height: AppTheme.space10),
          SkeletonLoader(width: double.infinity, height: 14, borderRadius: AppTheme.radiusXS),
          SizedBox(height: AppTheme.space8),
          SkeletonLoader(width: 200, height: 12, borderRadius: AppTheme.radiusXS),
          SizedBox(height: AppTheme.space16),
          SkeletonLoader(width: double.infinity, height: 44, borderRadius: AppTheme.radiusButton),
        ],
      ),
    );
  }
}

/// Ready-made skeleton loader for notification items
class NotificationItemSkeleton extends StatelessWidget {
  const NotificationItemSkeleton({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: AppTheme.space8),
      padding: const EdgeInsets.all(AppTheme.space12),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(AppTheme.radiusMedium),
        border: Border.all(color: AppTheme.border),
      ),
      child: const Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SkeletonLoader(width: 40, height: 40, borderRadius: 20),
          SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SkeletonLoader(width: 160, height: 15, borderRadius: AppTheme.radiusXS),
                SizedBox(height: 6),
                SkeletonLoader(width: double.infinity, height: 12, borderRadius: AppTheme.radiusXS),
                SizedBox(height: 6),
                SkeletonLoader(width: 80, height: 10, borderRadius: AppTheme.radiusXS),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Ready-made skeleton loader for full donation detail screens
class DonationDetailSkeleton extends StatelessWidget {
  const DonationDetailSkeleton({super.key});

  @override
  Widget build(BuildContext context) {
    return const SingleChildScrollView(
      padding: EdgeInsets.all(AppTheme.space16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header Card
          DonationCardSkeleton(),
          SizedBox(height: AppTheme.space16),
          // Live Tracking Card Skeleton
          DashboardStatsSkeleton(),
          SizedBox(height: AppTheme.space16),
          // Action button skeleton
          SkeletonLoader(width: double.infinity, height: 50, borderRadius: AppTheme.radiusButton),
        ],
      ),
    );
  }
}

