import 'package:flutter/material.dart';
import '../../core/localization/app_locale.dart';
import '../../core/models/auth_models.dart';
import '../../core/theme/app_theme.dart';

class _RoleOption {
  final UserRole role;
  final String labelKey;
  final IconData icon;
  const _RoleOption(this.role, this.labelKey, this.icon);
}

/// Role chips for registration. By default, public self-registration displays
/// the 3 primary operational roles (Donor, NGO, Volunteer). When [showAdmin] is
/// enabled (controlled admin provisioning mode), Admin is also selectable with
/// strict setup credential enforcement.
class RoleSelector extends StatelessWidget {
  final UserRole? selected;
  final ValueChanged<UserRole> onChanged;
  final bool showAdmin;

  const RoleSelector({
    super.key,
    required this.selected,
    required this.onChanged,
    this.showAdmin = false,
  });

  static const List<_RoleOption> _options = [
    _RoleOption(UserRole.donor, 'role_donor', Icons.storefront_outlined),
    _RoleOption(UserRole.ngo, 'role_ngo', Icons.apartment_outlined),
    _RoleOption(
        UserRole.volunteer, 'role_volunteer', Icons.pedal_bike_outlined),
    _RoleOption(
        UserRole.admin, 'role_admin', Icons.admin_panel_settings_outlined),
  ];

  @override
  Widget build(BuildContext context) {
    final availableOptions = showAdmin
        ? _options
        : _options.where((o) => o.role != UserRole.admin).toList();

    return Row(
      children: availableOptions.map((option) {
        final bool isSelected = option.role == selected;
        return Expanded(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4),
            child: Semantics(
              button: true,
              selected: isSelected,
              label: AppLocale.t(option.labelKey),
              child: InkWell(
                borderRadius: BorderRadius.circular(10),
                onTap: () => onChanged(option.role),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 150),
                  padding: const EdgeInsets.symmetric(vertical: 10),
                  decoration: BoxDecoration(
                    color: isSelected
                        ? AppColors.sabziGreen
                        : AppColors.surfaceWhite,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: isSelected
                          ? AppColors.sabziGreen
                          : AppColors.hairline,
                    ),
                  ),
                  child: Column(
                    children: [
                      Icon(
                        option.icon,
                        size: 20,
                        color: isSelected ? Colors.white : AppColors.deepSabzi,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        AppLocale.t(option.labelKey),
                        style: AppTextStyles.bodySmall.copyWith(
                          color:
                              isSelected ? Colors.white : AppColors.deepSabzi,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        );
      }).toList(),
    );
  }
}
