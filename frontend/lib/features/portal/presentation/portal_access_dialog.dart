import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/portal_access_repository.dart';
import '../providers/portal_providers.dart';

/// Staff dialog to open, reset, or revoke a customer's/supplier's portal
/// login. [resource] is "customers" or "suppliers".
Future<void> showPortalAccessDialog(
  BuildContext context, {
  required String resource,
  required String id,
  required String name,
}) {
  return showDialog(
    context: context,
    builder: (context) => _PortalAccessDialog(resource: resource, id: id, name: name),
  );
}

class _PortalAccessDialog extends ConsumerStatefulWidget {
  const _PortalAccessDialog({required this.resource, required this.id, required this.name});
  final String resource;
  final String id;
  final String name;

  @override
  ConsumerState<_PortalAccessDialog> createState() => _PortalAccessDialogState();
}

class _PortalAccessDialogState extends ConsumerState<_PortalAccessDialog> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  PortalAccessStatus? _status;
  bool _loading = true;
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final status = await ref.read(portalAccessRepositoryProvider).fetch(widget.resource, widget.id);
      if (!mounted) return;
      setState(() {
        _status = status;
        _emailController.text = status.email ?? '';
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _error = 'Could not load portal access.';
        _loading = false;
      });
    }
  }

  Future<void> _grant() async {
    final email = _emailController.text.trim();
    final password = _passwordController.text;
    if (email.isEmpty || password.length < 8) {
      setState(() => _error = 'Enter an email and a password of at least 8 characters.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final status = await ref.read(portalAccessRepositoryProvider)
          .grant(widget.resource, widget.id, email: email, password: password);
      if (!mounted) return;
      setState(() {
        _status = status;
        _passwordController.clear();
        _busy = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Portal access saved.')),
      );
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _error = 'That email may already be in use by another portal account.';
        _busy = false;
      });
    }
  }

  Future<void> _revoke() async {
    setState(() => _busy = true);
    try {
      await ref.read(portalAccessRepositoryProvider).revoke(widget.resource, widget.id);
      if (!mounted) return;
      setState(() {
        _status = const PortalAccessStatus(hasAccess: false);
        _busy = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Portal access revoked.')),
      );
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _error = 'Could not revoke access.';
        _busy = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final hasAccess = _status?.hasAccess ?? false;
    return AlertDialog(
      title: Text('Portal access · ${widget.name}'),
      content: _loading
          ? const SizedBox(height: 80, child: Center(child: CircularProgressIndicator()))
          : Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  hasAccess
                      ? 'This contact can sign in to the portal. Set a new password to reset it.'
                      : 'Create a login so this contact can view their documents in the portal.',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _emailController,
                  decoration: const InputDecoration(labelText: 'Login email'),
                  keyboardType: TextInputType.emailAddress,
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: _passwordController,
                  obscureText: true,
                  decoration: InputDecoration(
                    labelText: hasAccess ? 'New password' : 'Password',
                    helperText: 'At least 8 characters',
                  ),
                ),
                if (_error != null) ...[
                  const SizedBox(height: 8),
                  Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                ],
              ],
            ),
      actions: [
        if (hasAccess && !_loading)
          TextButton(
            onPressed: _busy ? null : _revoke,
            child: Text('Revoke', style: TextStyle(color: Theme.of(context).colorScheme.error)),
          ),
        TextButton(
          onPressed: _busy ? null : () => Navigator.of(context).pop(),
          child: const Text('Close'),
        ),
        FilledButton(
          onPressed: (_busy || _loading) ? null : _grant,
          child: _busy
              ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2))
              : Text(hasAccess ? 'Reset' : 'Grant access'),
        ),
      ],
    );
  }
}
