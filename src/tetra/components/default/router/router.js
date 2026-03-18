export default {
    init() {
        // Watch global route store for path changes
        // This makes Router components reactive to Tetra.navigate() calls
        this.$watch('$store.route.path', (newPath) => {
            // Only update if the path actually changed
        Tetra.debug('Router path changed:', newPath)
            if (this.current_path !== newPath) {
                this.handleRouteChange(newPath)
            }
        })

    },
    async handleRouteChange(newPath) {
        // Update current path immediately (optimistic)
        this.current_path = newPath

        // Trigger component refresh from server
        // The server will re-run navigate() in load() and match the new route
        // Then {% router_view %} will render the newly matched component
        await this._updateHtml()
    },
    __rootBind: {
        '@popstate.window': 'handleRouteChange(window.location.pathname)',
        '@tetra:navigate.window': 'handleRouteChange($event.detail.path)',
    }
}
