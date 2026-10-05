import { useState } from "react";
import { Container, Fab, Tooltip } from "@mui/material";
import { MessageCircle } from "lucide-react";
import { AppHeader } from "./components/AppHeader";
import { Hero } from "./components/Hero";
import { WorkloadToolbar } from "./components/WorkloadToolbar";
import { WorkloadTable } from "./components/WorkloadTable";
import { WorkloadPagination } from "./components/WorkloadPagination";
import { WorkItemDrawer } from "./components/WorkItemDrawer";
import ChatPopper from "./components/ChatPopper";
import { useMailbox } from "./hooks/useMailbox";
import type { Item } from "./types/mailbox";

// #region props interface
export interface AppProps {
  mode: "light" | "dark";
  onToggleMode: () => void;
}
// #endregion

const App = ({ mode, onToggleMode }: AppProps) => {
  // #region Custom Hooks
  const mailbox = useMailbox();
  // #endregion

  // #region State
  const [chatOpen, setChatOpen] = useState<boolean>(false);
  const [chatThread, setChatThread] = useState<Item | null>(null);
  const [chatSessionToken, setChatSessionToken] = useState(0);
  // #endregion

  // #region Function
  /**
   * Closes the chat popout and clears the currently selected chat thread.
   *
   * @returns void.
   */
  const handleCloseChat = (): void => {
    setChatOpen(false);
    setChatThread(null);
  };
  // #endregion

  return (
    <>
      <AppHeader
        status={mailbox.status}
        onRefresh={() => void mailbox.refresh()}
        mode={mode}
        onToggleMode={onToggleMode}
      />
      <Container
        maxWidth="xl"
        component="main"
        sx={{ py: { xs: 3.5, md: 5.5 } }}
      >
        <Hero counts={mailbox.counts} />
        <WorkloadToolbar
          filter={mailbox.filter}
          search={mailbox.search}
          count={mailbox.total}
          onFilter={mailbox.setFilter}
          onSearch={mailbox.setSearch}
        />
        <WorkloadTable
          items={mailbox.items}
          onOpen={mailbox.openItem}
          onDone={(item) => void mailbox.setDoneState(item, true)}
          onIncomplete={(item) => void mailbox.setDoneState(item, false)}
        />
        <WorkloadPagination
          page={mailbox.page}
          totalPages={mailbox.totalPages}
          from={mailbox.visibleRange.from}
          to={mailbox.visibleRange.to}
          total={mailbox.total}
          onPageChange={mailbox.changePage}
        />
      </Container>
      <WorkItemDrawer
        item={mailbox.selected}
        thread={mailbox.selectedThread}
        threadLoading={mailbox.threadLoading}
        analyzing={mailbox.analyzing}
        onClose={mailbox.closeDrawer}
        onDone={() => {
          if (mailbox.selected)
            void mailbox.setDoneState(mailbox.selected, true);
        }}
        onIncomplete={() => {
          if (mailbox.selected)
            void mailbox.setDoneState(mailbox.selected, false);
        }}
        onAskFollowUp={() => {
          if (!mailbox.selected) return;
          setChatThread(mailbox.selected);
          setChatSessionToken((value) => value + 1);
          setChatOpen(true);
          mailbox.closeDrawer();
        }}
      />
      <Tooltip title="Open mailbox assistant">
        <Fab
          color="primary"
          onClick={() => {
            setChatThread(null);
            setChatOpen(true);
          }}
          sx={{
            position: "fixed",
            right: { xs: 16, md: 24 },
            bottom: { xs: 16, md: 24 },
            borderRadius: 1,
            display: chatOpen ? "none" : "inline-flex",
          }}
          aria-label="Open mailbox assistant"
        >
          <MessageCircle size={21} />
        </Fab>
      </Tooltip>
      <ChatPopper
        open={chatOpen}
        onClose={handleCloseChat}
        thread={chatThread}
        newSessionToken={chatSessionToken}
      />
    </>
  );
};

export default App;
