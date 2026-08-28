import 'package:flutter/material.dart';
import '../core/theme/app_theme.dart';

/// One-handed large 6-digit numeric OTP keypad optimized for real-world volunteer handover verification.
class OtpInputWidget extends StatefulWidget {
  final ValueChanged<String> onCompleted;
  final bool isLoading;
  final String? errorMessage;

  const OtpInputWidget({
    super.key,
    required this.onCompleted,
    this.isLoading = false,
    this.errorMessage,
  });

  @override
  State<OtpInputWidget> createState() => _OtpInputWidgetState();
}

class _OtpInputWidgetState extends State<OtpInputWidget> {
  String _code = '';

  void _onKeyPress(String key) {
    if (_code.length < 6) {
      setState(() {
        _code += key;
      });
      if (_code.length == 6) {
        widget.onCompleted(_code);
      }
    }
  }

  void _onBackspace() {
    if (_code.isNotEmpty) {
      setState(() {
        _code = _code.substring(0, _code.length - 1);
      });
    }
  }

  void _onClear() {
    setState(() {
      _code = '';
    });
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        // 6-digit boxes
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: List.generate(6, (index) {
            final isFilled = index < _code.length;
            final isCurrent = index == _code.length;
            return Container(
              margin: const EdgeInsets.symmetric(horizontal: AppTheme.space4),
              width: 44,
              height: 54,
              decoration: BoxDecoration(
                color: isFilled ? AppTheme.primaryGreen.withValues(alpha: 0.06) : AppTheme.card,
                borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
                border: Border.all(
                  color: isCurrent
                      ? AppTheme.primaryGreen
                      : (isFilled ? AppTheme.primaryGreen.withValues(alpha: 0.4) : AppTheme.border),
                  width: isCurrent ? 2 : 1,
                ),
              ),
              child: Center(
                child: Text(
                  isFilled ? _code[index] : '',
                  style: const TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.bold,
                    color: AppTheme.textPrimary,
                  ),
                ),
              ),
            );
          }),
        ),
        if (widget.errorMessage != null && widget.errorMessage!.isNotEmpty) ...[
          const SizedBox(height: AppTheme.space12),
          Text(
            widget.errorMessage!,
            style: const TextStyle(
              color: AppTheme.error,
              fontSize: 13,
              fontWeight: FontWeight.w600,
            ),
            textAlign: TextAlign.center,
          ),
        ],
        const SizedBox(height: AppTheme.space24),
        // Big Touch Keypad
        Container(
          padding: const EdgeInsets.symmetric(horizontal: AppTheme.space16),
          child: Column(
            children: [
              _buildRow(['1', '2', '3']),
              const SizedBox(height: AppTheme.space12),
              _buildRow(['4', '5', '6']),
              const SizedBox(height: AppTheme.space12),
              _buildRow(['7', '8', '9']),
              const SizedBox(height: AppTheme.space12),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  _buildSpecialButton('C', _onClear),
                  _buildKeyButton('0'),
                  _buildSpecialButton('⌫', _onBackspace),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildRow(List<String> keys) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
      children: keys.map((k) => _buildKeyButton(k)).toList(),
    );
  }

  Widget _buildKeyButton(String val) {
    return SizedBox(
      width: 72,
      height: 60,
      child: OutlinedButton(
        onPressed: widget.isLoading ? null : () => _onKeyPress(val),
        style: OutlinedButton.styleFrom(
          backgroundColor: AppTheme.card,
          side: const BorderSide(color: AppTheme.border),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppTheme.radiusCard),
          ),
          padding: EdgeInsets.zero,
        ),
        child: Text(
          val,
          style: const TextStyle(
            fontSize: 24,
            fontWeight: FontWeight.bold,
            color: AppTheme.textPrimary,
          ),
        ),
      ),
    );
  }

  Widget _buildSpecialButton(String val, VoidCallback action) {
    return SizedBox(
      width: 72,
      height: 60,
      child: OutlinedButton(
        onPressed: widget.isLoading ? null : action,
        style: OutlinedButton.styleFrom(
          backgroundColor: AppTheme.background,
          side: const BorderSide(color: AppTheme.border),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppTheme.radiusCard),
          ),
          padding: EdgeInsets.zero,
        ),
        child: Text(
          val,
          style: const TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.w600,
            color: AppTheme.textSecondary,
          ),
        ),
      ),
    );
  }
}
