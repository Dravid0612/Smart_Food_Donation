import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../core/localization/app_locale.dart';
import '../../providers/donation_provider.dart';
import '../../models/certificate_model.dart';
import '../../widgets/loading_indicator.dart';

class DonationCertificateScreen extends StatefulWidget {
  final int donationId;

  const DonationCertificateScreen({super.key, required this.donationId});

  @override
  State<DonationCertificateScreen> createState() => _DonationCertificateScreenState();
}

class _DonationCertificateScreenState extends State<DonationCertificateScreen> {
  CertificateModel? _certificate;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      final cert = await Provider.of<DonationProvider>(context, listen: false)
          .fetchCertificate(widget.donationId);
      if (mounted) {
        setState(() {
          _certificate = cert;
          _isLoading = false;
        });
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.white),
          onPressed: () => context.pop(),
        ),
        title: Text(
          context.tr('certificate'),
          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.share, color: Colors.white),
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text(context.tr('certificate')),
                  backgroundColor: const Color(0xFF10B981),
                ),
              );
            },
          ),
        ],
      ),
      body: _isLoading
          ? LoadingIndicatorWidget(message: context.tr('processing'))
          : _certificate == null
              ? Center(
                  child: Text(
                    context.tr('no_donations'),
                    style: const TextStyle(color: Colors.white70),
                  ),
                )
              : SingleChildScrollView(
                  padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                  child: Column(
                    children: [
                      // Certificate Container
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(24),
                        decoration: BoxDecoration(
                          color: const Color(0xFF1E293B),
                          borderRadius: BorderRadius.circular(24),
                          border: Border.all(
                            color: const Color(0xFFF59E0B).withValues(alpha: 0.6),
                            width: 2,
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: const Color(0xFFF59E0B).withValues(alpha: 0.15),
                              blurRadius: 20,
                              offset: const Offset(0, 8),
                            ),
                          ],
                        ),
                        child: Column(
                          children: [
                            // Official Seal / Logo
                            Container(
                              padding: const EdgeInsets.all(16),
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                color: const Color(0xFFF59E0B).withValues(alpha: 0.15),
                                border: Border.all(color: const Color(0xFFF59E0B), width: 1.5),
                              ),
                              child: const Icon(
                                Icons.workspace_premium,
                                color: Color(0xFFF59E0B),
                                size: 48,
                              ),
                            ),
                            const SizedBox(height: 16),

                            // Certificate Title
                            Text(
                              context.tr('certificate').toUpperCase(),
                              style: const TextStyle(
                                color: Color(0xFFF59E0B),
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                                letterSpacing: 1.5,
                              ),
                              textAlign: TextAlign.center,
                            ),
                            const SizedBox(height: 20),

                            // Donor Name
                            Text(
                              _certificate!.donorName,
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 24,
                                fontWeight: FontWeight.bold,
                              ),
                              textAlign: TextAlign.center,
                            ),
                            const SizedBox(height: 4),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                              decoration: BoxDecoration(
                                color: const Color(0xFF10B981).withValues(alpha: 0.2),
                                borderRadius: BorderRadius.circular(20),
                              ),
                              child: Text(
                                context.trRole(_certificate!.organizationType),
                                style: const TextStyle(color: Color(0xFF10B981), fontSize: 12, fontWeight: FontWeight.w600),
                              ),
                            ),
                            const SizedBox(height: 16),

                            Text(
                              '${_certificate!.quantity.toStringAsFixed(0)} ${context.trUnit(_certificate!.quantityUnit)} • ${context.trFood(_certificate!.foodName)}',
                              style: TextStyle(color: Colors.grey.shade300, fontSize: 13, height: 1.5),
                              textAlign: TextAlign.center,
                            ),
                            const SizedBox(height: 20),

                            // Environmental Impact Stats
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                              decoration: BoxDecoration(
                                color: Colors.black26,
                                borderRadius: BorderRadius.circular(16),
                                border: Border.all(color: Colors.white10),
                              ),
                              child: Row(
                                mainAxisAlignment: MainAxisAlignment.spaceAround,
                                children: [
                                  Column(
                                    children: [
                                      const Icon(Icons.eco, color: Color(0xFF10B981), size: 22),
                                      const SizedBox(height: 4),
                                      Text(
                                        '${_certificate!.co2SavedKg} kg',
                                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
                                      ),
                                      Text(context.tr('co2_saved'), style: const TextStyle(color: Colors.white54, fontSize: 11)),
                                    ],
                                  ),
                                  Container(height: 30, width: 1, color: Colors.white12),
                                  Column(
                                    children: [
                                      const Icon(Icons.volunteer_activism, color: Colors.amber, size: 22),
                                      const SizedBox(height: 4),
                                      Text(
                                        _certificate!.quantity.toStringAsFixed(0),
                                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
                                      ),
                                      Text(context.tr('meals_rescued'), style: const TextStyle(color: Colors.white54, fontSize: 11)),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(height: 20),

                            // Metadata & Verification Hash
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text('ID', style: TextStyle(color: Colors.grey.shade500, fontSize: 10)),
                                    Text(
                                      _certificate!.certificateId,
                                      style: const TextStyle(color: Colors.white70, fontSize: 11, fontWeight: FontWeight.w600),
                                    ),
                                  ],
                                ),
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.end,
                                  children: [
                                    Row(
                                      children: [
                                        const Icon(Icons.verified, color: Color(0xFF10B981), size: 14),
                                        const SizedBox(width: 4),
                                        Text(context.tr('verified_partner'), style: const TextStyle(color: Color(0xFF10B981), fontSize: 10, fontWeight: FontWeight.bold)),
                                      ],
                                    ),
                                  ],
                                ),
                              ],
                            ),
                            const SizedBox(height: 16),
                            const Divider(color: Colors.white12),
                            const SizedBox(height: 8),

                            // Formal Disclaimer
                            Text(
                              context.trDisclaimer(),
                              style: TextStyle(color: Colors.grey.shade500, fontSize: 10, fontStyle: FontStyle.italic),
                              textAlign: TextAlign.center,
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 20),

                      // Download / Share Action
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton.icon(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0xFF10B981),
                            foregroundColor: Colors.white,
                            padding: const EdgeInsets.symmetric(vertical: 16),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                          ),
                          icon: const Icon(Icons.share),
                          label: Text(
                            context.tr('certificate'),
                            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                          ),
                          onPressed: () {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(
                                content: Text(context.tr('certificate')),
                                backgroundColor: const Color(0xFF10B981),
                              ),
                            );
                          },
                        ),
                      ),
                    ],
                  ),
                ),
    );
  }
}
