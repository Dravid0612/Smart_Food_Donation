import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/app_state.dart';

class CreateDonationPage extends StatefulWidget {
  const CreateDonationPage({super.key});

  @override
  State<CreateDonationPage> createState() => _CreateDonationPageState();
}

class _CreateDonationPageState extends State<CreateDonationPage> {
  final _foodNameController = TextEditingController();
  final _quantityController = TextEditingController();
  final _preparationController = TextEditingController();
  final _expiryController = TextEditingController();
  final _addressController = TextEditingController();
  final _latitudeController = TextEditingController();
  final _longitudeController = TextEditingController();

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    return Scaffold(
      appBar: AppBar(title: const Text('Create Donation')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            children: [
              TextField(controller: _foodNameController, decoration: const InputDecoration(labelText: 'Food name')),
              const SizedBox(height: 12),
              TextField(controller: _quantityController, decoration: const InputDecoration(labelText: 'Quantity')),
              const SizedBox(height: 12),
              TextField(controller: _preparationController, decoration: const InputDecoration(labelText: 'Preparation time')),
              const SizedBox(height: 12),
              TextField(controller: _expiryController, decoration: const InputDecoration(labelText: 'Expiry time')),
              const SizedBox(height: 12),
              TextField(controller: _addressController, decoration: const InputDecoration(labelText: 'Pickup address')),
              const SizedBox(height: 12),
              TextField(controller: _latitudeController, decoration: const InputDecoration(labelText: 'Latitude')),
              const SizedBox(height: 12),
              TextField(controller: _longitudeController, decoration: const InputDecoration(labelText: 'Longitude')),
              const SizedBox(height: 20),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: () async {
                    if (auth.token == null) return;
                    final donation = {
                      'food_name': _foodNameController.text,
                      'quantity': _quantityController.text,
                      'preparation_time': _preparationController.text,
                      'expiry_time': _expiryController.text,
                      'pickup_address': _addressController.text,
                      'latitude': double.tryParse(_latitudeController.text) ?? 0.0,
                      'longitude': double.tryParse(_longitudeController.text) ?? 0.0,
                      'status': 'pending',
                    };
                    try {
                      await context.read<DonationProvider>().createDonation(auth.token!, donation);
                      if (mounted) Navigator.of(context).pop();
                    } catch (error) {
                      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.toString())));
                    }
                  },
                  child: const Text('Submit Donation'),
                ),
              )
            ],
          ),
        ),
      ),
    );
  }
}
