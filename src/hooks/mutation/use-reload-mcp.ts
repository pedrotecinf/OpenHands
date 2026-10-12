import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import AgentServerConversationService from "#/api/conversation-service/agent-server-conversation-service.api";
import { I18nKey } from "#/i18n/declaration";
import { displaySuccessToast } from "#/utils/custom-toast-handlers";
import { invalidateConversationQueries } from "./conversation-mutation-utils";

export function useReloadMCP() {
  const queryClient = useQueryClient();
  const { t } = useTranslation("openhands");
  return useMutation({
    mutationFn: (conversationId: string) =>
      AgentServerConversationService.reloadMCP(conversationId),
    onSuccess: (result, conversationId) => {
      invalidateConversationQueries(queryClient, conversationId);
      displaySuccessToast(
        t(I18nKey.CONVERSATION$MCP_RELOADED, {
          servers: result.servers.join(", ") || "—",
        }),
      );
    },
  });
}
