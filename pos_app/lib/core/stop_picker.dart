import 'package:flutter/material.dart';

/// Campo de origem/destino com pesquisa por escrita: em vez de rolar o
/// dropdown com a lista inteira de paragens, abre uma folha com caixa de
/// texto que filtra a medida que o agente escreve.
class StopPickerField extends StatelessWidget {
  const StopPickerField({
    super.key,
    required this.label,
    required this.stops,
    required this.selectedId,
    required this.onChanged,
    this.excludeId,
    this.icon,
  });

  final String label;
  final List<dynamic> stops;
  final int? selectedId;
  final int? excludeId;
  final ValueChanged<int?> onChanged;
  final Widget? icon;

  @override
  Widget build(BuildContext context) {
    Map? selected;
    for (final s in stops) {
      if (s is Map && s['id'] == selectedId) selected = s;
    }
    return InkWell(
      borderRadius: BorderRadius.circular(8),
      onTap: () async {
        final picked = await _showSearchSheet(context);
        if (picked != null) onChanged(picked['id'] as int?);
      },
      child: InputDecorator(
        decoration: InputDecoration(
          labelText: label,
          prefixIcon: icon,
          suffixIcon: const Icon(Icons.search, size: 20),
        ),
        isEmpty: selected == null,
        child: Text(
          selected?['name']?.toString() ?? 'Toque para procurar...',
          style: selected == null
              ? TextStyle(color: Theme.of(context).hintColor)
              : const TextStyle(fontWeight: FontWeight.w600),
        ),
      ),
    );
  }

  Future<Map?> _showSearchSheet(BuildContext context) {
    return showModalBottomSheet<Map>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (ctx) => _StopSearchSheet(title: label, stops: stops, excludeId: excludeId),
    );
  }
}

class _StopSearchSheet extends StatefulWidget {
  const _StopSearchSheet({required this.title, required this.stops, this.excludeId});

  final String title;
  final List<dynamic> stops;
  final int? excludeId;

  @override
  State<_StopSearchSheet> createState() => _StopSearchSheetState();
}

class _StopSearchSheetState extends State<_StopSearchSheet> {
  String _query = '';

  String _norm(String s) {
    const from = 'áàâãäéèêëíìîïóòôõöúùûüç';
    const to = 'aaaaaeeeeiiiiooooouuuuc';
    var out = s.toLowerCase();
    for (var i = 0; i < from.length; i++) {
      out = out.replaceAll(from[i], to[i]);
    }
    return out;
  }

  @override
  Widget build(BuildContext context) {
    final q = _norm(_query.trim());
    final visible = [
      for (final s in widget.stops)
        if (s is Map &&
            s['id'] != widget.excludeId &&
            (q.isEmpty || _norm('${s['name']} ${s['code'] ?? ''}').contains(q)))
          s,
    ];
    return Padding(
      // Sobe com o teclado para a lista continuar visivel enquanto escreve.
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: SizedBox(
        height: MediaQuery.of(context).size.height * 0.72,
        child: Column(children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 4),
            child: Row(children: [
              Expanded(
                child: Text(widget.title,
                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
              ),
              IconButton(icon: const Icon(Icons.close), onPressed: () => Navigator.pop(context)),
            ]),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
            child: TextField(
              autofocus: true,
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.search, size: 20),
                hintText: 'Escreva o nome da paragem...',
              ),
              onChanged: (v) => setState(() => _query = v),
            ),
          ),
          Expanded(
            child: visible.isEmpty
                ? const Center(
                    child: Text('Nenhuma paragem com esse nome.',
                        style: TextStyle(fontSize: 13)),
                  )
                : ListView.builder(
                    itemCount: visible.length,
                    itemBuilder: (ctx, i) {
                      final s = visible[i];
                      final code = (s['code'] ?? '').toString();
                      return ListTile(
                        dense: true,
                        leading: const Icon(Icons.place_outlined, size: 20),
                        title: Text(s['name']?.toString() ?? '-'),
                        subtitle: code.isEmpty ? null : Text(code, style: const TextStyle(fontSize: 11)),
                        onTap: () => Navigator.pop(context, s),
                      );
                    },
                  ),
          ),
        ]),
      ),
    );
  }
}
