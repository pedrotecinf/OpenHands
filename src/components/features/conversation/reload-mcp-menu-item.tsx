import { RefreshCw } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useReloadMCP } from "#/hooks/mutation/use-reload-mcp";
import { I18nKey } from "#/i18n/declaration";
import { ContextMenuListItem } from "../context-menu/context-menu-list-item";
import { ConversationNameContextMenuIconText } from "./conversation-name-context-menu-icon-text";

export function ReloadMcpMenuItem({
  conversationId,
  isDisabled,
  onClose,
}: {
  conversationId: string;
  isDisabled: boolean;
  onClose: () => void;
}) {
  const { t } = useTranslation("openhands");
  const reloadMCP = useReloadMCP();
  return (
    <ContextMenuListItem
      testId="reload-mcp-button"
      isDisabled={isDisabled || reloadMCP.isPending}
      onClick={() => {
        reloadMCP.mutate(conversationId);
        onClose();
      }}
    >
      <ConversationNameContextMenuIconText
        icon={<RefreshCw size={16} />}
        text={t(I18nKey.CONVERSATION$RELOAD_MCP)}
      />
    </ContextMenuListItem>
  );
}
