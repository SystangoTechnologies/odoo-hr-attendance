import { patch } from "@web/core/utils/patch";
import { WebClient } from "@web/webclient/webclient";

patch(WebClient.prototype, {
    get _canSendNativeNotification() {
        return false;
    },
});
