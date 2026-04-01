export default {
    init() {
        // Only root routers actively watch the route store and handle navigation.
        // Nested (child) routers are passive — they get re-rendered by the parent
        // router via {% router_view %} and receive _remaining_path through context.
        if (this.is_root_router) {
            this.$watch('$store.route.path', (newPath) => {
                Tetra.debug('Router path changed:', newPath)
                if (this.current_path !== newPath) {
                    this.handleRouteChange(newPath)
                }
            })
        }
    },
    async handleRouteChange(newPath) {
        // Guard: only root routers handle route changes
        if (!this.is_root_router) return;

        // Update current path immediately (optimistic)
        this.current_path = newPath

        // Trigger component refresh from server.
        // The server re-runs navigate() in load() and matches the new route,
        // then {% router_view %} renders the matched component (including any
        // nested child routers that handle sub-routes).
        await this._updateHtml()
    },
    __rootBind: {
        '@popstate.window': 'handleRouteChange(window.location.pathname)',
        '@tetra:navigate.window': 'handleRouteChange($event.detail.path)',
    }
}
