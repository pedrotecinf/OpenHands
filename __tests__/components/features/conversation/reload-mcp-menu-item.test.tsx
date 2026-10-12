import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "test-utils";
import AgentServerConversationService from "#/api/conversation-service/agent-server-conversation-service.api";
import { ReloadMcpMenuItem } from "#/components/features/conversation/reload-mcp-menu-item";

describe("MCP reload action", () => {
  it("reloads the existing conversation without creating or running another", async () => {
    const reload = vi
      .spyOn(AgentServerConversationService, "reloadMCP")
      .mockResolvedValue({
        servers: ["new-mcp"],
        tools: ["marker"],
        session_resumed: true,
        agent_kind: "acp",
      });
    const onClose = vi.fn();
    renderWithProviders(
      <ReloadMcpMenuItem
        conversationId="existing-conversation"
        isDisabled={false}
        onClose={onClose}
      />,
    );
    await userEvent.click(screen.getByTestId("reload-mcp-button"));
    await waitFor(() =>
      expect(reload).toHaveBeenCalledWith("existing-conversation"),
    );
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("does not reload a running conversation", async () => {
    const reload = vi.spyOn(AgentServerConversationService, "reloadMCP");
    reload.mockClear();
    renderWithProviders(
      <ReloadMcpMenuItem
        conversationId="running-conversation"
        isDisabled
        onClose={vi.fn()}
      />,
    );
    await userEvent.click(screen.getByTestId("reload-mcp-button"));
    expect(reload).not.toHaveBeenCalled();
  });
});
