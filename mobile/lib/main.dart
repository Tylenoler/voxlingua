import 'package:flutter/material.dart';

void main() {
  runApp(const VoxLinguaApp());
}

class VoxLinguaApp extends StatelessWidget {
  const VoxLinguaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'VoxLingua',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.blueGrey,
          brightness: Brightness.light,
        ),
        useMaterial3: true,
      ),
      home: const ChatScreen(),
    );
  }
}

class ChatScreen extends StatelessWidget {
  const ChatScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('VoxLingua')),
      body: const Center(
        child: Text('AI Voice Language Tutor'),
      ),
    );
  }
}
