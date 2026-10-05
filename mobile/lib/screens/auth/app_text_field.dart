import 'package:flutter/material.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';

/// Shared text field for every auth screen, so login and registration
/// never drift into two different visual styles for the same kind of
/// input.
class AppTextField extends StatefulWidget {
  final String label;
  final String hint;
  final TextEditingController controller;
  final bool obscureText;
  final TextInputType keyboardType;
  final String? Function(String?)? validator;
  final String? semanticLabel;

  const AppTextField({
    super.key,
    required this.label,
    required this.hint,
    required this.controller,
    this.obscureText = false,
    this.keyboardType = TextInputType.text,
    this.validator,
    this.semanticLabel,
  });

  @override
  State<AppTextField> createState() => _AppTextFieldState();
}

class _AppTextFieldState extends State<AppTextField> {
  late bool _obscured;

  @override
  void initState() {
    super.initState();
    // Set in initState rather than at field declaration — `widget` isn't
    // safely readable in a field initializer before the State is attached.
    _obscured = widget.obscureText;
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(widget.label, style: AppTextStyles.label),
        const SizedBox(height: 6),
        Semantics(
          label: widget.semanticLabel ?? widget.label,
          textField: true,
          child: TextFormField(
            controller: widget.controller,
            obscureText: _obscured,
            keyboardType: widget.keyboardType,
            style: AppTextStyles.body,
            validator: widget.validator,
            decoration: InputDecoration(
              hintText: widget.hint,
              suffixIcon: widget.obscureText
                  ? IconButton(
                      icon: Icon(
                        _obscured
                            ? Icons.visibility_outlined
                            : Icons.visibility_off_outlined,
                        color: AppColors.sageGrey,
                        size: 20,
                      ),
                      tooltip: _obscured
                          ? AppLocale.t('show_password')
                          : AppLocale.t('hide_password'),
                      onPressed: () => setState(() => _obscured = !_obscured),
                    )
                  : null,
            ),
          ),
        ),
      ],
    );
  }
}
