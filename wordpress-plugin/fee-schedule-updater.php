<?php
/**
 * Plugin Name: Fee Schedule Auto-Updater
 * Description: Fetches the latest passport fee schedule PDF from GitHub Pages and saves it locally, keeping the existing download URL intact.
 * Version: 1.1
 */

defined('ABSPATH') || exit;

define('FSU_SOURCE_URL', 'https://circlerktech.github.io/passport-fee-api/Fee-Schedule.pdf');
define('FSU_DEST_PATH',  WP_CONTENT_DIR . '/uploads/2026/06/Fee-Schedule.pdf');

// ── Activation / Deactivation ─────────────────────────────────────────────────

register_activation_hook(__FILE__, function () {
    if (!wp_next_scheduled('fsu_daily_fetch')) {
        wp_schedule_event(time(), 'daily', 'fsu_daily_fetch');
    }
    // Generate a webhook secret once on activation so GitHub Actions can
    // trigger an immediate fetch the moment it commits a fee change.
    if (!get_option('fsu_webhook_secret')) {
        update_option('fsu_webhook_secret', wp_generate_password(32, false));
    }
});

register_deactivation_hook(__FILE__, function () {
    wp_clear_scheduled_hook('fsu_daily_fetch');
});

// ── Fetch logic ───────────────────────────────────────────────────────────────

add_action('fsu_daily_fetch', 'fsu_fetch');

function fsu_fetch(): void {
    $response = wp_remote_get(FSU_SOURCE_URL, ['timeout' => 30]);

    if (is_wp_error($response)) {
        update_option('fsu_last_error',  $response->get_error_message());
        update_option('fsu_last_check',  current_time('mysql'));
        return;
    }

    $code = wp_remote_retrieve_response_code($response);
    if ($code !== 200) {
        update_option('fsu_last_error',  "HTTP $code from source");
        update_option('fsu_last_check',  current_time('mysql'));
        return;
    }

    $dir = dirname(FSU_DEST_PATH);
    if (!is_dir($dir)) {
        wp_mkdir_p($dir);
    }

    $bytes = file_put_contents(FSU_DEST_PATH, wp_remote_retrieve_body($response));
    $ok    = ($bytes !== false);

    update_option('fsu_last_check', current_time('mysql'));

    if ($ok) {
        update_option('fsu_last_updated', current_time('mysql'));
        delete_option('fsu_last_error');
    } else {
        update_option('fsu_last_error', 'File write failed — check folder permissions');
    }
}

// ── Webhook endpoint ──────────────────────────────────────────────────────────
// GitHub Actions calls POST /wp-json/fee-schedule/v1/fetch with the secret
// in the X-Fee-Schedule-Secret header immediately after committing a fee
// change — no more relying on WP-Cron timing to eventually catch up.

add_action('rest_api_init', function () {
    register_rest_route('fee-schedule/v1', '/fetch', [
        'methods'             => 'POST',
        'callback'            => 'fsu_handle_webhook',
        'permission_callback' => '__return_true',
    ]);
});

function fsu_handle_webhook(WP_REST_Request $request): WP_REST_Response {
    $expected = get_option('fsu_webhook_secret', '');
    $provided = $request->get_header('x_fee_schedule_secret');

    if (empty($expected) || !hash_equals($expected, (string) $provided)) {
        return new WP_REST_Response(['error' => 'Unauthorized'], 401);
    }

    fsu_fetch();

    $error = get_option('fsu_last_error', '');
    if ($error) {
        return new WP_REST_Response(['success' => false, 'error' => $error], 500);
    }
    return new WP_REST_Response([
        'success'      => true,
        'last_updated' => get_option('fsu_last_updated'),
    ], 200);
}

// ── Admin page ────────────────────────────────────────────────────────────────

add_action('admin_menu', function () {
    add_management_page(
        'Fee Schedule Updater',
        'Fee Schedule PDF',
        'manage_options',
        'fee-schedule-updater',
        'fsu_admin_page'
    );
});

function fsu_admin_page(): void {
    if (!current_user_can('manage_options')) {
        return;
    }

    $notice = '';

    if (isset($_POST['fsu_fetch_now']) && check_admin_referer('fsu_fetch')) {
        fsu_fetch();
        $error = get_option('fsu_last_error', '');
        $notice = $error
            ? "<div class='notice notice-error'><p>Error: " . esc_html($error) . "</p></div>"
            : "<div class='notice notice-success'><p>PDF updated successfully.</p></div>";
    }

    if (isset($_POST['fsu_regenerate_secret']) && check_admin_referer('fsu_regenerate')) {
        update_option('fsu_webhook_secret', wp_generate_password(32, false));
        $notice = "<div class='notice notice-warning'><p>Webhook secret regenerated. Update the <strong>WP_WEBHOOK_SECRET</strong> GitHub secret with the new value below.</p></div>";
    }

    $last_check    = get_option('fsu_last_check',      'Never');
    $last_updated  = get_option('fsu_last_updated',    'Never');
    $last_error    = get_option('fsu_last_error',      '');
    $next_run      = wp_next_scheduled('fsu_daily_fetch');
    $webhook_secret = get_option('fsu_webhook_secret', '');
    $webhook_url   = rest_url('fee-schedule/v1/fetch');

    echo $notice;
    ?>
    <div class="wrap">
        <h1>Fee Schedule Auto-Updater</h1>
        <table class="widefat" style="max-width:700px;margin-top:16px">
            <tr><th>Source</th><td><?php echo esc_html(FSU_SOURCE_URL); ?></td></tr>
            <tr><th>Destination</th><td><?php echo esc_html(FSU_DEST_PATH); ?></td></tr>
            <tr><th>Last checked</th><td><?php echo esc_html($last_check); ?></td></tr>
            <tr><th>Last updated</th><td><?php echo esc_html($last_updated); ?></td></tr>
            <tr><th>Next scheduled run</th><td><?php echo $next_run ? esc_html(date('Y-m-d H:i:s', $next_run)) : 'Not scheduled'; ?></td></tr>
            <?php if ($last_error): ?>
            <tr><th>Last error</th><td style="color:red"><?php echo esc_html($last_error); ?></td></tr>
            <?php endif; ?>
        </table>

        <h2 style="margin-top:24px">GitHub Actions Webhook</h2>
        <p>Add these two values as <strong>Repository Secrets</strong> in GitHub so the action can trigger an immediate fetch the moment fees are updated:</p>
        <table class="widefat" style="max-width:700px">
            <tr>
                <th style="width:180px">WP_WEBHOOK_URL</th>
                <td><code><?php echo esc_html($webhook_url); ?></code></td>
            </tr>
            <tr>
                <th>WP_WEBHOOK_SECRET</th>
                <td><code><?php echo esc_html($webhook_secret); ?></code></td>
            </tr>
        </table>
        <form method="post" style="margin-top:8px">
            <?php wp_nonce_field('fsu_regenerate'); ?>
            <input type="submit" name="fsu_regenerate_secret" class="button" value="Regenerate Secret">
        </form>

        <h2 style="margin-top:24px">Manual Fetch</h2>
        <form method="post">
            <?php wp_nonce_field('fsu_fetch'); ?>
            <input type="submit" name="fsu_fetch_now" class="button button-primary" value="Fetch PDF Now">
        </form>
    </div>
    <?php
}
