#import <Cocoa/Cocoa.h>
#import <WebKit/WebKit.h>

@interface Studio : NSObject <NSApplicationDelegate, WKScriptMessageHandler, WKNavigationDelegate>
@property NSWindow *window;
@property NSURL *address;
@property NSSize normalSize;
@property BOOL compact;
@property NSVisualEffectView *glass;
@end
@implementation Studio
- (void)applicationDidFinishLaunching:(NSNotification *)notification {
    WKWebViewConfiguration *config = [WKWebViewConfiguration new];
    [config.userContentController addScriptMessageHandler:self name:@"windowControl"];
    [config.userContentController addUserScript:[[WKUserScript alloc] initWithSource:@"window.irisNativeGlass=true;" injectionTime:WKUserScriptInjectionTimeAtDocumentStart forMainFrameOnly:YES]];
    NSString *bridge = @"window.pywebview={api:{glass:function(v){window.webkit.messageHandlers.windowControl.postMessage({action:'glass',value:v,dark:matchMedia('(prefers-color-scheme: dark)').matches});return Promise.resolve();},compact:function(v){window.webkit.messageHandlers.windowControl.postMessage({action:'compact',value:v});return Promise.resolve({compact:v});},minimize:function(){window.webkit.messageHandlers.windowControl.postMessage({action:'minimize'});return Promise.resolve();}}};window.dispatchEvent(new Event('pywebviewready'));";
    [config.userContentController addUserScript:[[WKUserScript alloc] initWithSource:bridge injectionTime:WKUserScriptInjectionTimeAtDocumentEnd forMainFrameOnly:YES]];
    WKWebView *view = [[WKWebView alloc] initWithFrame:NSZeroRect configuration:config];
    view.navigationDelegate = self;
    // WKWebView otherwise paints an opaque backing even with transparent CSS.
    [view setValue:@NO forKey:@"drawsBackground"];
    if (@available(macOS 12.0, *)) view.underPageBackgroundColor = NSColor.clearColor;
    view.autoresizingMask = NSViewWidthSizable | NSViewHeightSizable;
    self.window = [[NSWindow alloc] initWithContentRect:NSMakeRect(0,0,1220,860) styleMask:NSWindowStyleMaskTitled|NSWindowStyleMaskClosable|NSWindowStyleMaskMiniaturizable|NSWindowStyleMaskResizable backing:NSBackingStoreBuffered defer:NO];
    self.window.title = @"Iris Studio · Eye HCI";
    self.window.minSize = NSMakeSize(380,420);
    self.window.opaque = NO;
    self.window.backgroundColor = NSColor.clearColor;
    self.window.titlebarAppearsTransparent = YES;
    self.glass = [[NSVisualEffectView alloc] initWithFrame:NSMakeRect(0,0,1220,860)];
    self.glass.blendingMode = NSVisualEffectBlendingModeBehindWindow;
    self.glass.material = NSVisualEffectMaterialHUDWindow;
    self.glass.state = NSVisualEffectStateActive;
    self.glass.autoresizingMask = NSViewWidthSizable | NSViewHeightSizable;
    self.glass.hidden = YES;
    NSView *container = [[NSView alloc] initWithFrame:NSMakeRect(0,0,1220,860)];
    [container addSubview:self.glass];
    view.frame = container.bounds;
    [container addSubview:view];
    self.window.contentView = container;
    self.window.releasedWhenClosed = NO;
    [self.window center];
    [self.window makeKeyAndOrderFront:nil];
    [NSApp activateIgnoringOtherApps:YES];
    [view loadRequest:[NSURLRequest requestWithURL:self.address]];
}
- (BOOL)localURL:(NSURL *)url {
    return [url.scheme isEqual:self.address.scheme] && [url.host isEqual:self.address.host] && [url.port isEqual:self.address.port];
}
- (void)userContentController:(WKUserContentController *)controller didReceiveScriptMessage:(WKScriptMessage *)message {
    if (!message.frameInfo.mainFrame || ![self localURL:message.frameInfo.request.URL] || ![message.body isKindOfClass:[NSDictionary class]]) return;
    NSDictionary *body = message.body;
    if ([body[@"action"] isEqual:@"glass"]) {
        if ([body[@"value"] isKindOfClass:[NSNumber class]]) {
            self.glass.hidden = ![body[@"value"] boolValue];
            self.glass.appearance = [NSAppearance appearanceNamed:[body[@"dark"] boolValue] ? NSAppearanceNameDarkAqua : NSAppearanceNameAqua];
        }
        return;
    }
    if ([body[@"action"] isEqual:@"minimize"]) { [self.window miniaturize:nil]; return; }
    if (![body[@"action"] isEqual:@"compact"] || ![body[@"value"] isKindOfClass:[NSNumber class]]) return;
    BOOL enabled = [body[@"value"] boolValue];
    if (enabled && !self.compact) self.normalSize = self.window.frame.size;
    self.compact = enabled;
    self.window.level = enabled ? NSFloatingWindowLevel : NSNormalWindowLevel;
    self.window.collectionBehavior = enabled ? NSWindowCollectionBehaviorCanJoinAllSpaces|NSWindowCollectionBehaviorFullScreenAuxiliary : NSWindowCollectionBehaviorDefault;
    NSRect frame = self.window.frame;
    NSSize size = enabled ? NSMakeSize(420,570) : self.normalSize;
    frame.origin.y += frame.size.height-size.height;
    frame.size = size;
    [self.window setFrame:frame display:YES animate:YES];
}
- (void)webView:(WKWebView *)webView decidePolicyForNavigationAction:(WKNavigationAction *)action decisionHandler:(void (^)(WKNavigationActionPolicy))decisionHandler {
    decisionHandler([self localURL:action.request.URL] ? WKNavigationActionPolicyAllow : WKNavigationActionPolicyCancel);
}
- (BOOL)applicationShouldTerminateAfterLastWindowClosed:(NSApplication *)sender { return YES; }
@end
int main(int argc, const char *argv[]) {
    @autoreleasepool {
        if (argc != 2) return 1;
        NSURL *address = [NSURL URLWithString:[NSString stringWithUTF8String:argv[1]]];
        if (![address.scheme isEqual:@"http"] || ![address.host isEqual:@"127.0.0.1"]) return 1;
        NSApplication *app = [NSApplication sharedApplication];
        [app setActivationPolicy:NSApplicationActivationPolicyRegular];
        Studio *studio = [Studio new];
        studio.address = address;
        app.delegate = studio;
        [app run];
    }
    return 0;
}
