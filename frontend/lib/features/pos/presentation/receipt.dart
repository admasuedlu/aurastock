import 'package:intl/intl.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:printing/printing.dart';

import '../domain/pos_models.dart';

/// Builds an 80mm thermal-roll receipt for a completed POS sale and hands it to
/// the platform print flow. On web this opens the browser's print dialog (which
/// can target a thermal printer); on desktop/mobile it shows the print UI.
Future<void> printPosReceipt(PosTransaction txn) async {
  final currency = NumberFormat.currency(symbol: 'ETB ', decimalDigits: 2);
  final stamp = DateFormat('yyyy-MM-dd  HH:mm').format(DateTime.now());

  final doc = pw.Document();
  doc.addPage(
    pw.Page(
      pageFormat: PdfPageFormat.roll80,
      margin: const pw.EdgeInsets.all(6),
      build: (context) => pw.Column(
        crossAxisAlignment: pw.CrossAxisAlignment.stretch,
        children: [
          pw.Center(
            child: pw.Text('AuraStock', style: pw.TextStyle(fontSize: 15, fontWeight: pw.FontWeight.bold)),
          ),
          pw.Center(child: pw.Text('Sales Receipt', style: const pw.TextStyle(fontSize: 9))),
          pw.SizedBox(height: 6),
          pw.Text('Receipt: ${txn.number}', style: const pw.TextStyle(fontSize: 9)),
          pw.Text('Date:    $stamp', style: const pw.TextStyle(fontSize: 9)),
          if (txn.customerName.isNotEmpty)
            pw.Text('Customer: ${txn.customerName}', style: const pw.TextStyle(fontSize: 9)),
          pw.Divider(height: 8),
          for (final item in txn.items)
            pw.Row(
              mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
              children: [
                pw.Expanded(
                  child: pw.Text('${item.productName}  x${_qty(item.quantity)}',
                      style: const pw.TextStyle(fontSize: 9)),
                ),
                pw.Text(currency.format(item.lineTotal), style: const pw.TextStyle(fontSize: 9)),
              ],
            ),
          pw.Divider(height: 8),
          _row('TOTAL', currency.format(txn.total), bold: true),
          _row('Paid (${txn.paymentMethod})', currency.format(txn.amountTendered)),
          if (txn.paymentMethod == 'cash') _row('Change', currency.format(txn.changeDue)),
          pw.SizedBox(height: 10),
          pw.Center(child: pw.Text('Thank you!', style: const pw.TextStyle(fontSize: 10))),
        ],
      ),
    ),
  );

  await Printing.layoutPdf(name: 'Receipt ${txn.number}', onLayout: (format) => doc.save());
}

String _qty(double q) => q == q.roundToDouble() ? q.toStringAsFixed(0) : q.toStringAsFixed(2);

pw.Widget _row(String label, String value, {bool bold = false}) {
  final style = pw.TextStyle(fontSize: 9, fontWeight: bold ? pw.FontWeight.bold : pw.FontWeight.normal);
  return pw.Row(
    mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
    children: [pw.Text(label, style: style), pw.Text(value, style: style)],
  );
}
