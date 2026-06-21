import 'package:flutter/material.dart';
import '../models/types.dart';

class CorrectionDisplay extends StatelessWidget {
  final CorrectionResult correction;

  const CorrectionDisplay({super.key, required this.correction});

  Color _levelColor() {
    switch (correction.level) {
      case "severe":
        return Colors.red;
      case "medium":
        return Colors.orange;
      default:
        return Colors.green;
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final levelColor = _levelColor();

    return Container(
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest.withOpacity(0.5),
        borderRadius: BorderRadius.circular(8),
        border: Border(left: BorderSide(color: levelColor, width: 3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                "Score: ${correction.overallScore.toStringAsFixed(0)}",
                style: theme.textTheme.labelLarge?.copyWith(fontWeight: FontWeight.bold),
              ),
              Text(
                correction.level.toUpperCase(),
                style: theme.textTheme.labelLarge?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: levelColor,
                ),
              ),
            ],
          ),

          // Phoneme errors (up to 3)
          if (correction.errors.isNotEmpty) ...[
            const SizedBox(height: 8),
            ...correction.errors.take(3).map((err) => Padding(
              padding: const EdgeInsets.symmetric(vertical: 2),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: theme.colorScheme.surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(err.phoneme, style: const TextStyle(fontFamily: "monospace", fontWeight: FontWeight.bold)),
                  ),
                  const Padding(
                    padding: EdgeInsets.symmetric(horizontal: 4),
                    child: Icon(Icons.arrow_forward, size: 14),
                  ),
                  Text(err.actual, style: const TextStyle(fontFamily: "monospace", fontWeight: FontWeight.bold, color: Colors.red)),
                  const SizedBox(width: 4),
                  Expanded(
                    child: Text(err.feedback, style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurfaceVariant)),
                  ),
                ],
              ),
            )),
            if (correction.errors.length > 3)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text("+${correction.errors.length - 3} more errors",
                  style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurfaceVariant)),
              ),
          ],

          // Score bars
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 4,
            children: [
              _scoreBar("Accuracy", correction.dimensions.phonemeAccuracy, theme),
              _scoreBar("Fluency", correction.dimensions.fluency, theme),
              _scoreBar("Prosody", correction.dimensions.prosody, theme),
              _scoreBar("Complete", correction.dimensions.completeness, theme),
            ],
          ),
        ],
      ),
    );
  }

  Widget _scoreBar(String label, double value, ThemeData theme) {
    return SizedBox(
      width: 140,
      child: Row(
        children: [
          SizedBox(width: 50, child: Text(label, style: theme.textTheme.bodySmall)),
          Expanded(
            child: ClipRRect(
              borderRadius: BorderRadius.circular(2),
              child: LinearProgressIndicator(
                value: value / 100,
                backgroundColor: theme.colorScheme.surfaceContainerHighest,
                color: Theme.of(this.context).colorScheme.primary,
              ),
            ),
          ),
          SizedBox(
            width: 28,
            child: Text(value.toStringAsFixed(0), textAlign: TextAlign.right, style: theme.textTheme.bodySmall),
          ),
        ],
      ),
    );
  }
}
