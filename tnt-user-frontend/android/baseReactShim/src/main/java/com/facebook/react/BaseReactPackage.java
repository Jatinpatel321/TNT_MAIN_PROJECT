package com.facebook.react;

import androidx.annotation.Nullable;
import com.facebook.react.bridge.ModuleSpec;
import com.facebook.react.bridge.NativeModule;
import com.facebook.react.bridge.ReactApplicationContext;
import com.facebook.react.module.model.ReactModuleInfo;
import com.facebook.react.module.model.ReactModuleInfoProvider;
import com.facebook.react.uimanager.ViewManager;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import javax.inject.Provider;

/**
 * Compatibility shim for libraries that still extend the legacy BaseReactPackage class that was
 * removed in React Native 0.73. The implementation mirrors the historical behaviour closely enough
 * for popular libraries (react-native-svg, react-native-screens, etc.) to keep working.
 */
public abstract class BaseReactPackage extends LazyReactPackage
    implements ViewManagerOnDemandReactPackage {

  @Override
  protected List<ModuleSpec> getNativeModules(final ReactApplicationContext reactContext) {
    final ReactModuleInfoProvider infoProvider = getReactModuleInfoProvider();
    final Map<String, ReactModuleInfo> moduleInfos = infoProvider.getReactModuleInfos();
    if (moduleInfos == null || moduleInfos.isEmpty()) {
      return Collections.emptyList();
    }

    final List<ModuleSpec> specs = new ArrayList<>(moduleInfos.size());
    for (final Map.Entry<String, ReactModuleInfo> entry : moduleInfos.entrySet()) {
      final String moduleName = entry.getKey();
      specs.add(
          ModuleSpec.nativeModuleSpec(
              moduleName,
              new Provider<NativeModule>() {
                @Override
                public NativeModule get() {
                  NativeModule module = BaseReactPackage.this.getModule(moduleName, reactContext);
                  if (module == null) {
                    throw new IllegalStateException(
                        "Unable to create native module " + moduleName + " from BaseReactPackage");
                  }
                  return module;
                }
              }));
    }
    return specs;
  }

  @Override
  public ReactModuleInfoProvider getReactModuleInfoProvider() {
    return LazyReactPackage.getReactModuleInfoProviderViaReflection(this);
  }

  @Nullable
  public NativeModule getModule(String name, ReactApplicationContext reactContext) {
    return null;
  }

  @Nullable
  @Override
  public List<String> getViewManagerNames(ReactApplicationContext reactContext) {
    return Collections.emptyList();
  }

  @Nullable
  @Override
  public ViewManager createViewManager(
      ReactApplicationContext reactContext, String viewManagerName) {
    return null;
  }
}
