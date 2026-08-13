import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:geolocator/geolocator.dart';
import 'package:intl/intl.dart';
import '../../providers/donation_provider.dart';

class CreateDonationScreen extends StatefulWidget {
  const CreateDonationScreen({super.key});

  @override
  State<CreateDonationScreen> createState() => _CreateDonationScreenState();
}

class _CreateDonationScreenState extends State<CreateDonationScreen> {
  final _formKey = GlobalKey<FormState>();
  final _foodNameController = TextEditingController();
  final _quantityController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _addressController = TextEditingController();

  String _category = 'Cooked Food';
  String _unit = 'Meals';
  DateTime _prepTime = DateTime.now();
  DateTime _expiryTime = DateTime.now().add(const Duration(hours: 6));
  double? _latitude = 12.9716;
  double? _longitude = 77.5946;
  XFile? _pickedImage;
  bool _isLocating = false;

  final List<String> _categories = [
    'Cooked Food',
    'Bakery',
    'Fruits',
    'Vegetables',
    'Packaged Food',
    'Other'
  ];

  final List<String> _units = ['Meals', 'Kg', 'Litres', 'Packets'];

  @override
  void dispose() {
    _foodNameController.dispose();
    _quantityController.dispose();
    _descriptionController.dispose();
    _addressController.dispose();
    super.dispose();
  }

  Future<void> _pickImage(ImageSource source) async {
    final picker = ImagePicker();
    final image = await picker.pickImage(source: source, imageQuality: 80);
    if (image != null) {
      setState(() => _pickedImage = image);
    }
  }

  Future<void> _getCurrentLocation() async {
    setState(() => _isLocating = true);
    try {
      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.whileInUse || permission == LocationPermission.always) {
        Position position = await Geolocator.getCurrentPosition();
        setState(() {
          _latitude = position.latitude;
          _longitude = position.longitude;
          _addressController.text = 'Current GPS Location (${position.latitude.toStringAsFixed(4)}, ${position.longitude.toStringAsFixed(4)})';
        });
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Could not fetch GPS location. Enter address manually.')),
      );
    } finally {
      setState(() => _isLocating = false);
    }
  }

  Future<void> _selectDateTime(BuildContext context, bool isPrep) async {
    final initial = isPrep ? _prepTime : _expiryTime;
    final date = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime.now().subtract(const Duration(days: 1)),
      lastDate: DateTime.now().add(const Duration(days: 14)),
    );

    if (date != null && mounted) {
      final time = await showTimePicker(
        context: context,
        initialTime: TimeOfDay.fromDateTime(initial),
      );

      if (time != null) {
        setState(() {
          final selected = DateTime(date.year, date.month, date.day, time.hour, time.minute);
          if (isPrep) {
            _prepTime = selected;
          } else {
            _expiryTime = selected;
          }
        });
      }
    }
  }

  Future<void> _handleSubmit() async {
    if (!_formKey.currentState!.validate()) return;

    if (_expiryTime.isBefore(DateTime.now())) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Expiry time must be in the future.'), backgroundColor: Colors.redAccent),
      );
      return;
    }

    final quantity = double.tryParse(_quantityController.text.trim()) ?? 0;
    if (quantity <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Quantity must be greater than zero.'), backgroundColor: Colors.redAccent),
      );
      return;
    }

    final provider = Provider.of<DonationProvider>(context, listen: false);
    final success = await provider.createDonation(
      foodName: _foodNameController.text.trim(),
      foodCategory: _category,
      quantity: quantity,
      quantityUnit: _unit,
      preparationTime: _prepTime,
      expiryTime: _expiryTime,
      pickupAddress: _addressController.text.trim().isEmpty ? 'Pickup Location' : _addressController.text.trim(),
      description: _descriptionController.text.trim(),
      latitude: _latitude,
      longitude: _longitude,
      imageUrl: 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=400',
    );

    if (!mounted) return;

    if (success) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Food Donation Created Successfully! 🎉'), backgroundColor: Color(0xFF10B981)),
      );
      context.go('/donor');
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(provider.errorMessage ?? 'Failed to create donation'), backgroundColor: Colors.redAccent),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<DonationProvider>(context);
    final dateFormat = DateFormat('MMM dd, yyyy - hh:mm a');

    return Scaffold(
      appBar: AppBar(
        title: const Text('Donate Food'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/donor'),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Image Picker Box
              GestureDetector(
                onTap: () {
                  showModalBottomSheet(
                    context: context,
                    builder: (_) => SafeArea(
                      child: Wrap(
                        children: [
                          ListTile(
                            leading: const Icon(Icons.camera_alt),
                            title: const Text('Camera'),
                            onTap: () {
                              Navigator.pop(context);
                              _pickImage(ImageSource.camera);
                            },
                          ),
                          ListTile(
                            leading: const Icon(Icons.photo_library),
                            title: const Text('Gallery'),
                            onTap: () {
                              Navigator.pop(context);
                              _pickImage(ImageSource.gallery);
                            },
                          ),
                        ],
                      ),
                    ),
                  );
                },
                child: Container(
                  height: 160,
                  decoration: BoxDecoration(
                    color: Colors.grey.shade100,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: Colors.grey.shade300, style: BorderStyle.solid),
                  ),
                  child: _pickedImage != null
                      ? ClipRRect(
                          borderRadius: BorderRadius.circular(16),
                          child: Image.file(File(_pickedImage!.path), fit: BoxFit.cover),
                        )
                      : Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: const [
                            Icon(Icons.add_a_photo_outlined, size: 40, color: Color(0xFF10B981)),
                            SizedBox(height: 8),
                            Text('Upload Food Photo', style: TextStyle(color: Color(0xFF64748B))),
                          ],
                        ),
                ),
              ),
              const SizedBox(height: 20),

              // Food Name
              TextFormField(
                controller: _foodNameController,
                decoration: const InputDecoration(
                  labelText: 'Food Name *',
                  hintText: 'e.g. Vegetable Rice, Packaged Lunch',
                  prefixIcon: Icon(Icons.fastfood_outlined),
                ),
                validator: (v) => v == null || v.trim().isEmpty ? 'Please enter food name' : null,
              ),
              const SizedBox(height: 16),

              // Category & Unit Row
              Row(
                children: [
                  Expanded(
                    child: DropdownButtonFormField<String>(
                      value: _category,
                      decoration: const InputDecoration(labelText: 'Category *'),
                      items: _categories.map((c) => DropdownMenuItem(value: c, child: Text(c))).toList(),
                      onChanged: (val) => setState(() => _category = val!),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: DropdownButtonFormField<String>(
                      value: _unit,
                      decoration: const InputDecoration(labelText: 'Unit *'),
                      items: _units.map((u) => DropdownMenuItem(value: u, child: Text(u))).toList(),
                      onChanged: (val) => setState(() => _unit = val!),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Quantity
              TextFormField(
                controller: _quantityController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Quantity *',
                  hintText: 'e.g. 50',
                  prefixIcon: Icon(Icons.numbers),
                ),
                validator: (v) {
                  if (v == null || v.trim().isEmpty) return 'Enter quantity';
                  final num = double.tryParse(v);
                  if (num == null || num <= 0) return 'Must be > 0';
                  return null;
                },
              ),
              const SizedBox(height: 16),

              // Preparation & Expiry Pickers
              ListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Preparation Time'),
                subtitle: Text(dateFormat.format(_prepTime)),
                trailing: const Icon(Icons.calendar_today, color: Color(0xFF10B981)),
                onTap: () => _selectDateTime(context, true),
              ),
              const Divider(),
              ListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Expiry Time *'),
                subtitle: Text(
                  dateFormat.format(_expiryTime),
                  style: const TextStyle(color: Colors.redAccent, fontWeight: FontWeight.bold),
                ),
                trailing: const Icon(Icons.access_time_filled, color: Colors.redAccent),
                onTap: () => _selectDateTime(context, false),
              ),
              const Divider(),
              const SizedBox(height: 12),

              // Pickup Address & Location
              TextFormField(
                controller: _addressController,
                decoration: InputDecoration(
                  labelText: 'Pickup Address *',
                  prefixIcon: const Icon(Icons.location_on_outlined),
                  suffixIcon: IconButton(
                    icon: _isLocating
                        ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                        : const Icon(Icons.my_location, color: Color(0xFF10B981)),
                    onPressed: _getCurrentLocation,
                  ),
                ),
                validator: (v) => v == null || v.trim().isEmpty ? 'Enter pickup location' : null,
              ),
              const SizedBox(height: 16),

              // Description
              TextFormField(
                controller: _descriptionController,
                maxLines: 3,
                decoration: const InputDecoration(
                  labelText: 'Description (Optional)',
                  hintText: 'Add preparation notes or storage recommendations...',
                ),
              ),
              const SizedBox(height: 28),

              // Submit Button
              ElevatedButton(
                onPressed: provider.isLoading ? null : _handleSubmit,
                child: provider.isLoading
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                      )
                    : const Text('Submit Donation'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
